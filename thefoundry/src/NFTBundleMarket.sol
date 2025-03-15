// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/token/ERC721/utils/ERC721Holder.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title NFTBundleMarket
 * @dev A marketplace for selling NFT bundles with Shapley value-based pricing
 */
contract NFTBundleMarket is ERC721Holder, Ownable, ReentrancyGuard {
    struct NFTItem {
        address nftContract;
        uint256 tokenId;
        address seller;
        bool sold;
    }

    struct Bundle {
        uint256[] itemIds;
        uint256 price;
        uint256 requiredBuyers;
        bool active;
        address[] interestedBuyers;
        mapping(address => bool) buyerInterested;
        bool completed;
    }

    // Events
    event NFTListed(uint256 indexed itemId, address indexed nftContract, uint256 indexed tokenId, address seller);
    event BundleCreated(uint256 indexed bundleId, uint256[] itemIds, uint256 price, uint256 requiredBuyers);
    event BuyerInterested(uint256 indexed bundleId, address buyer, uint256[] itemsOfInterest);
    event BundleReadyForPurchase(uint256 indexed bundleId, address[] buyers);
    event ShapleyValuesSet(uint256 indexed bundleId, address[] buyers, uint256[] values);
    event BundlePurchased(uint256 indexed bundleId, address[] buyers);
    event NFTWithdrawn(uint256 indexed itemId, address indexed seller);
    event AttestationRequested(uint256 indexed bundleId);
    event BundleCancelled(uint256 indexed bundleId);
    event BuyerPaid(uint256 indexed bundleId, address buyer, uint256 amount);

    // State variables
    uint256 private _itemIds;
    uint256 private _bundleIds;
    mapping(uint256 => NFTItem) public items;
    mapping(uint256 => Bundle) private bundles;
    mapping(uint256 => mapping(address => uint256)) public shapleyValues;
    mapping(uint256 => mapping(address => uint256[])) public buyerItemInterests;
    mapping(uint256 => mapping(address => bool)) public hasPaid;
    
    // Address that can set Shapley values (would be the TEE in production)
    address public shapleyCalculator;

    constructor() Ownable(msg.sender) {
        shapleyCalculator = msg.sender; // Initially set to contract deployer for testing
    }

    /**
     * @dev Sets the address that can calculate and set Shapley values
     */
    function setShapleyCalculator(address _calculator) external onlyOwner {
        shapleyCalculator = _calculator;
    }

    /**
     * @dev Lists an NFT for potential inclusion in bundles
     */
    function listNFT(address _nftContract, uint256 _tokenId) external nonReentrant returns (uint256) {
        _itemIds++;
        uint256 itemId = _itemIds;
        
        items[itemId] = NFTItem({
            nftContract: _nftContract,
            tokenId: _tokenId,
            seller: msg.sender,
            sold: false
        });
        
        // Transfer NFT to contract (escrow)
        IERC721(_nftContract).safeTransferFrom(msg.sender, address(this), _tokenId);
        
        emit NFTListed(itemId, _nftContract, _tokenId, msg.sender);
        
        return itemId;
    }

    /**
     * @dev Creates a bundle of NFTs with a total price
     */
    function createBundle(uint256[] calldata itemIdList, uint256 _price, uint256 _requiredBuyers) external nonReentrant returns (uint256) {
        require(itemIdList.length > 0, "Bundle must contain at least one item");
        require(_requiredBuyers > 0, "Required buyers must be greater than zero");
        
        // Check that all items exist, are not sold, and caller is the seller
        for (uint256 i = 0; i < itemIdList.length; i++) {
            uint256 itemId = itemIdList[i];
            require(itemId > 0 && itemId <= _itemIds, "Item does not exist");
            require(!items[itemId].sold, "Item already sold");
            require(items[itemId].seller == msg.sender, "Not the seller");
            
            // Check for duplicate items in the bundle
            for (uint256 j = 0; j < i; j++) {
                require(itemIdList[j] != itemId, "Duplicate item in bundle");
            }
        }
        
        _bundleIds++;
        uint256 bundleId = _bundleIds;
        
        Bundle storage newBundle = bundles[bundleId];
        newBundle.itemIds = itemIdList;
        newBundle.price = _price;
        newBundle.requiredBuyers = _requiredBuyers;
        newBundle.active = true;
        newBundle.completed = false;
        
        emit BundleCreated(bundleId, itemIdList, _price, _requiredBuyers);
        
        return bundleId;
    }

    /**
     * @dev Allows a buyer to express interest in a bundle and specify which items they're interested in
     */
    function expressInterest(uint256 _bundleId, uint256[] calldata _itemsOfInterest) external nonReentrant {
        Bundle storage bundle = bundles[_bundleId];
        
        require(bundle.active, "Bundle is not active");
        require(!bundle.completed, "Bundle already completed");
        require(!bundle.buyerInterested[msg.sender], "Already expressed interest");
        require(_itemsOfInterest.length > 0, "Must be interested in at least one item");
        
        // Validate that all items of interest are in the bundle
        for (uint256 i = 0; i < _itemsOfInterest.length; i++) {
            bool found = false;
            for (uint256 j = 0; j < bundle.itemIds.length; j++) {
                if (_itemsOfInterest[i] == bundle.itemIds[j]) {
                    found = true;
                    break;
                }
            }
            require(found, "Item not in bundle");
        }
        
        bundle.buyerInterested[msg.sender] = true;
        bundle.interestedBuyers.push(msg.sender);
        buyerItemInterests[_bundleId][msg.sender] = _itemsOfInterest;
        
        emit BuyerInterested(_bundleId, msg.sender, _itemsOfInterest);
        
        // Check if we have enough buyers
        if (bundle.interestedBuyers.length >= bundle.requiredBuyers) {
            emit BundleReadyForPurchase(_bundleId, bundle.interestedBuyers);
        }
    }

    /**
     * @dev Request attestation for Shapley value calculation
     */
    function requestAttestation(uint256 _bundleId) external {
        Bundle storage bundle = bundles[_bundleId];
        
        require(bundle.active, "Bundle is not active");
        require(!bundle.completed, "Bundle already completed");
        require(bundle.interestedBuyers.length >= bundle.requiredBuyers, "Not enough interested buyers");
        
        emit AttestationRequested(_bundleId);
    }

    /**
     * @dev Sets Shapley values for a bundle (called by the TEE or authorized calculator)
     */
    function setShapleyValues(
        uint256 _bundleId, 
        address[] calldata _buyers, 
        uint256[] calldata _values
    ) external {
        require(msg.sender == shapleyCalculator, "Not authorized");
        require(_buyers.length == _values.length, "Arrays length mismatch");
        
        Bundle storage bundle = bundles[_bundleId];
        require(bundle.active, "Bundle is not active");
        require(!bundle.completed, "Bundle already completed");
        
        // Verify all buyers are interested in the bundle
        for (uint256 i = 0; i < _buyers.length; i++) {
            require(bundle.buyerInterested[_buyers[i]], "Buyer not interested");
            shapleyValues[_bundleId][_buyers[i]] = _values[i];
        }
        
        // Verify sum of Shapley values equals bundle price
        uint256 totalValue = 0;
        for (uint256 i = 0; i < _values.length; i++) {
            totalValue += _values[i];
        }
        require(totalValue == bundle.price, "Sum of Shapley values must equal bundle price");
        
        emit ShapleyValuesSet(_bundleId, _buyers, _values);
    }

    /**
     * @dev Completes a bundle purchase after Shapley values are set
     */
    function completeBundlePurchase(uint256 _bundleId) external payable nonReentrant {
        Bundle storage bundle = bundles[_bundleId];
        
        require(bundle.active, "Bundle is not active");
        require(!bundle.completed, "Bundle already completed");
        require(bundle.buyerInterested[msg.sender], "Not an interested buyer");
        require(!hasPaid[_bundleId][msg.sender], "Already paid");
        
        uint256 buyerValue = shapleyValues[_bundleId][msg.sender];
        require(buyerValue > 0, "Shapley value not set");
        require(msg.value >= buyerValue, "Insufficient payment");
        
        // Mark buyer as paid
        hasPaid[_bundleId][msg.sender] = true;
        
        // Refund excess payment if any
        if (msg.value > buyerValue) {
            payable(msg.sender).transfer(msg.value - buyerValue);
        }
        
        // Emit event for individual payment
        emit BuyerPaid(_bundleId, msg.sender, buyerValue);
        
        // Check if all buyers have paid
        bool allPaid = true;
        for (uint256 i = 0; i < bundle.interestedBuyers.length; i++) {
            if (!hasPaid[_bundleId][bundle.interestedBuyers[i]]) {
                allPaid = false;
                break;
            }
        }
        
        // Only complete the purchase if all buyers have paid
        if (allPaid) {
            // Calculate total payment
            uint256 totalPayment = 0;
            for (uint256 i = 0; i < bundle.interestedBuyers.length; i++) {
                address buyer = bundle.interestedBuyers[i];
                totalPayment += shapleyValues[_bundleId][buyer];
            }
            
            // Distribute to sellers proportionally
            for (uint256 i = 0; i < bundle.itemIds.length; i++) {
                uint256 itemId = bundle.itemIds[i];
                NFTItem memory item = items[itemId];
                // Calculate seller's share (could be more complex based on item value)
                uint256 sellerShare = totalPayment / bundle.itemIds.length;
                payable(item.seller).transfer(sellerShare);
            }
            
            // Mark items as sold
            for (uint256 i = 0; i < bundle.itemIds.length; i++) {
                uint256 itemId = bundle.itemIds[i];
                items[itemId].sold = true;
            }
            
            // Transfer NFTs to buyers based on their interests
            for (uint256 i = 0; i < bundle.interestedBuyers.length; i++) {
                address buyer = bundle.interestedBuyers[i];
                uint256[] memory buyerItems = buyerItemInterests[_bundleId][buyer];
                
                for (uint256 j = 0; j < buyerItems.length; j++) {
                    uint256 itemId = buyerItems[j];
                    NFTItem memory item = items[itemId];
                    
                    IERC721(item.nftContract).safeTransferFrom(
                        address(this),
                        buyer,
                        item.tokenId
                    );
                }
            }
            
            // Complete the bundle purchase
            bundle.completed = true;
            bundle.active = false;
            
            emit BundlePurchased(_bundleId, bundle.interestedBuyers);
        }
    }

    /**
     * @dev Allows a seller to withdraw their NFT if it hasn't been sold
     */
    function withdrawNFT(uint256 _itemId) external nonReentrant {
        NFTItem storage item = items[_itemId];
        
        require(item.seller == msg.sender, "Not the seller");
        require(!item.sold, "Item already sold");
        
        // Optimize gas usage with a more efficient check
        bool inActiveBundle = isItemInActiveBundle(_itemId);
        require(!inActiveBundle, "Item is in an active bundle");
        
        // Transfer NFT back to seller
        IERC721(item.nftContract).safeTransferFrom(
            address(this),
            msg.sender,
            item.tokenId
        );
        
        // Mark as withdrawn (not sold, but no longer available)
        item.sold = true;
        
        emit NFTWithdrawn(_itemId, msg.sender);
    }
    
    /**
     * @dev Helper function to check if an item is in an active bundle
     */
    function isItemInActiveBundle(uint256 _itemId) internal view returns (bool) {
        for (uint256 i = 1; i <= _bundleIds; i++) {
            Bundle storage bundle = bundles[i];
            if (!bundle.active) continue;
            
            for (uint256 j = 0; j < bundle.itemIds.length; j++) {
                if (bundle.itemIds[j] == _itemId) {
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * @dev Returns bundle information
     */
    function getBundleInfo(uint256 _bundleId) external view returns (
        uint256[] memory itemIds,
        uint256 price,
        uint256 requiredBuyers,
        bool active,
        address[] memory interestedBuyers,
        bool completed
    ) {
        Bundle storage bundle = bundles[_bundleId];
        return (
            bundle.itemIds,
            bundle.price,
            bundle.requiredBuyers,
            bundle.active,
            bundle.interestedBuyers,
            bundle.completed
        );
    }

    /**
     * @dev Returns the items a buyer is interested in for a specific bundle
     */
    function getBuyerInterests(uint256 _bundleId, address _buyer) external view returns (uint256[] memory) {
        return buyerItemInterests[_bundleId][_buyer];
    }

    /**
     * @dev Allows the bundle creator to cancel a bundle
     */
    function cancelBundle(uint256 _bundleId) external nonReentrant {
        Bundle storage bundle = bundles[_bundleId];
        require(bundle.active, "Bundle is not active");
        require(!bundle.completed, "Bundle already completed");
        
        // Verify all items in the bundle belong to the caller
        for (uint256 i = 0; i < bundle.itemIds.length; i++) {
            require(items[bundle.itemIds[i]].seller == msg.sender, "Not the seller of all items");
        }
        
        bundle.active = false;
        
        emit BundleCancelled(_bundleId);
    }
} 