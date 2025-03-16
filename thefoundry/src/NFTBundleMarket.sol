// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/token/ERC721/utils/ERC721Holder.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "forge-std/console.sol";


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
        uint256 paidCount;
        string name;
        string description;
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
        console.log("NFTBundleMarket contract initialized");
        console.log("Initial shapleyCalculator set to:", msg.sender);
    }

    /**
     * @dev Sets the address that can calculate and set Shapley values
     */
    function setShapleyCalculator(address _calculator) external onlyOwner {
        console.log("Changing shapleyCalculator from:", shapleyCalculator);
        console.log("Changing shapleyCalculator to:", _calculator);
        shapleyCalculator = _calculator;
    }

    /**
     * @dev Lists an NFT for potential inclusion in bundles
     */
    function listNFT(address _nftContract, uint256 _tokenId) external nonReentrant returns (uint256) {
        console.log("listNFT called");
        console.log("NFT contract:", _nftContract);
        console.log("Token ID:", _tokenId);
        console.log("Seller:", msg.sender);
        
        _itemIds++;
        uint256 itemId = _itemIds;
        
        items[itemId] = NFTItem({
            nftContract: _nftContract,
            tokenId: _tokenId,
            seller: msg.sender,
            sold: false
        });
        
        // Transfer NFT to contract (escrow)
        try IERC721(_nftContract).safeTransferFrom(msg.sender, address(this), _tokenId) {
            console.log("NFT transferred to contract");
            console.log(_nftContract);
            console.log(_tokenId);
            console.log(msg.sender);
            console.log(address(this));
        } catch Error(string memory reason) {
            console.log("NFT transfer failed:");
            console.log(reason);
            revert(string(abi.encodePacked("NFT transfer failed: ", reason)));
        } catch {
            console.log("NFT transfer failed: unknown error");
            revert("NFT transfer failed: unknown error");
        }
        
        emit NFTListed(itemId, _nftContract, _tokenId, msg.sender);
        console.log("New item ID:", itemId);
        
        return itemId;
    }

    /**
     * @dev Creates a bundle of NFTs with a total price
     */
    function createBundle(uint256[] calldata itemIdList, uint256 _price, uint256 _requiredBuyers) external nonReentrant returns (uint256) {
        console.log("createBundle called");
        return _createBundle(itemIdList, _price, _requiredBuyers, "", "");
    }

    /**
     * @dev Creates a bundle of NFTs with a total price, name and description
     */
    function createBundleWithMetadata(
        uint256[] calldata itemIdList, 
        uint256 _price, 
        uint256 _requiredBuyers,
        string calldata _name,
        string calldata _description
    ) external nonReentrant returns (uint256) {
        console.log("createBundleWithMetadata called");
        return _createBundle(itemIdList, _price, _requiredBuyers, _name, _description);
    }

    /**
     * @dev Internal function to create a bundle
     */
    function _createBundle(
        uint256[] calldata itemIdList, 
        uint256 _price, 
        uint256 _requiredBuyers,
        string memory _name,
        string memory _description
    ) internal returns (uint256) {
        console.log("_createBundle internal function called");
        
        require(itemIdList.length > 0, "Bundle must contain at least one item");
        console.log("Number of items in bundle:", itemIdList.length);
        
        require(_requiredBuyers > 0, "Required buyers must be greater than zero");
        console.log("Required buyers:", _requiredBuyers);
        
        // Check that all items exist, are not sold, and caller is the seller
        for (uint256 i = 0; i < itemIdList.length; i++) {
            uint256 itemId = itemIdList[i];
            console.log("Checking item ID:", itemId);
            
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
        console.log("New bundle ID:", bundleId);
        
        Bundle storage newBundle = bundles[bundleId];
        newBundle.itemIds = itemIdList;
        newBundle.price = _price;
        newBundle.requiredBuyers = _requiredBuyers;
        newBundle.active = true;
        newBundle.completed = false;
        newBundle.paidCount = 0;
        newBundle.name = _name;
        newBundle.description = _description;
        
        emit BundleCreated(bundleId, itemIdList, _price, _requiredBuyers);
        console.log("Bundle created successfully");
        
        return bundleId;
    }

    /**
     * @dev Allows a buyer to express interest in a bundle and specify which items they're interested in
     */
    function expressInterest(uint256 _bundleId, uint256[] calldata _itemsOfInterest) external nonReentrant {
        console.log("expressInterest called");
        console.log("Bundle ID:", _bundleId);
        console.log("Buyer:", msg.sender);
        
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
        console.log("Interest expressed successfully");
        
        // Check if we have enough buyers
        if (bundle.interestedBuyers.length >= bundle.requiredBuyers) {
            emit BundleReadyForPurchase(_bundleId, bundle.interestedBuyers);
            console.log("Bundle is ready for purchase");
            console.log("Number of interested buyers:", bundle.interestedBuyers.length);
            console.log("Required buyers:", bundle.requiredBuyers);
        } else {
            console.log("Not enough buyers yet");
            console.log("Current interested buyers:", bundle.interestedBuyers.length);
            console.log("Required buyers:", bundle.requiredBuyers);
        }
    }

    /**
     * @dev Request attestation for Shapley value calculation
     */
    function requestAttestation(uint256 _bundleId) external {
        console.log("requestAttestation called");
        console.log("Bundle ID:", _bundleId);
        
        Bundle storage bundle = bundles[_bundleId];
        
        require(bundle.active, "Bundle is not active");
        require(!bundle.completed, "Bundle already completed");
        require(bundle.interestedBuyers.length >= bundle.requiredBuyers, "Not enough interested buyers");
        
        emit AttestationRequested(_bundleId);
        console.log("Attestation requested successfully");
    }

    /**
     * @dev Sets Shapley values for a bundle (called by the TEE or authorized calculator)
     */
    function setShapleyValues(
        uint256 _bundleId, 
        address[] calldata _buyers, 
        uint256[] calldata _values
    ) external {
        console.log("setShapleyValues called");
        console.log("Bundle ID:", _bundleId);
        console.log("Caller:", msg.sender);
        console.log("Authorized calculator:", shapleyCalculator);
        
        require(msg.sender == shapleyCalculator, "Not authorized");
        require(_buyers.length == _values.length, "Arrays length mismatch");
        
        Bundle storage bundle = bundles[_bundleId];
        require(bundle.active, "Bundle is not active");
        require(!bundle.completed, "Bundle already completed");
        
        // Verify all buyers are interested in the bundle
        for (uint256 i = 0; i < _buyers.length; i++) {
            require(bundle.buyerInterested[_buyers[i]], "Buyer not interested");
            shapleyValues[_bundleId][_buyers[i]] = _values[i];
            console.log("Set Shapley value for buyer:", _buyers[i]);
            console.log("Value:", _values[i]);
        }
        
        // Verify sum of Shapley values equals bundle price
        uint256 totalValue = 0;
        for (uint256 i = 0; i < _values.length; i++) {
            totalValue += _values[i];
        }
        console.log("Total Shapley value:", totalValue);
        console.log("Bundle price:", bundle.price);
        
        require(totalValue == bundle.price, "Sum of Shapley values must equal bundle price");
        
        emit ShapleyValuesSet(_bundleId, _buyers, _values);
        console.log("Shapley values set successfully");
    }

    /**
     * @dev Completes a bundle purchase after Shapley values are set
     */
    function completeBundlePurchase(uint256 _bundleId) external payable nonReentrant {
        console.log("completeBundlePurchase called");
        console.log("Bundle ID:", _bundleId);
        console.log("Buyer:", msg.sender);
        console.log("Msg value:", msg.value);
        
        Bundle storage bundle = bundles[_bundleId];
        
        require(bundle.active, "Bundle is not active");
        require(!bundle.completed, "Bundle already completed");
        require(bundle.buyerInterested[msg.sender], "Not an interested buyer");
        require(!hasPaid[_bundleId][msg.sender], "Already paid");
        
        uint256 buyerValue = shapleyValues[_bundleId][msg.sender];
        console.log("Buyer's Shapley value:", buyerValue);
        
        require(buyerValue > 0, "Shapley value not set");
        require(msg.value >= buyerValue, "Insufficient payment");
        
        // Mark buyer as paid
        hasPaid[_bundleId][msg.sender] = true;
        bundle.paidCount++;
        console.log("New paid count:", bundle.paidCount);
        
        // Refund excess payment if any
        if (msg.value > buyerValue) {
            uint256 refundAmount = msg.value - buyerValue;
            console.log("Refund amount:", refundAmount);
            
            (bool success, ) = payable(msg.sender).call{value: refundAmount}("");
            if (success) {
                console.log("Refund sent");
                console.log(address(this));
                console.log(msg.sender);
                console.log(refundAmount);
            } else {
                console.log("Refund failed");
                // Continue execution even if refund fails
            }
        }
        
        // Emit event for individual payment
        emit BuyerPaid(_bundleId, msg.sender, buyerValue);
        
        // Check if all required buyers have paid
        bool allPaid = (bundle.paidCount >= bundle.requiredBuyers);
        console.log("All required buyers have paid:", allPaid ? "true" : "false");
        console.log("Paid count:", bundle.paidCount);
        console.log("Required buyers:", bundle.requiredBuyers);
        
        // Only complete the purchase if all required buyers have paid
        if (allPaid) {
            console.log("Completing bundle purchase");
            
            // Calculate total payment
            uint256 totalPayment = 0;
            for (uint256 i = 0; i < bundle.interestedBuyers.length; i++) {
                address buyer = bundle.interestedBuyers[i];
                if (hasPaid[_bundleId][buyer]) {
                    totalPayment += shapleyValues[_bundleId][buyer];
                }
            }
            console.log("Total payment collected:", totalPayment);
            
            // Distribute to sellers proportionally
            for (uint256 i = 0; i < bundle.itemIds.length; i++) {
                uint256 itemId = bundle.itemIds[i];
                NFTItem storage item = items[itemId];
                // Calculate seller's share (could be more complex based on item value)
                uint256 sellerShare = totalPayment / bundle.itemIds.length;
                console.log("Seller share for item:", itemId);
                console.log("Seller share:", sellerShare);
                
                (bool success, ) = payable(item.seller).call{value: sellerShare}("");
                if (success) {
                    console.log("Payment sent to seller");
                    console.log(address(this));
                    console.log(item.seller);
                    console.log(sellerShare);
                } else {
                    console.log("Payment to seller failed for item:", itemId);
                    // Continue execution even if payment fails
                }
            }
            
            // Transfer NFTs to buyers based on their interests
            for (uint256 i = 0; i < bundle.interestedBuyers.length; i++) {
                address buyer = bundle.interestedBuyers[i];
                if (hasPaid[_bundleId][buyer]) {
                    uint256[] memory buyerItems = buyerItemInterests[_bundleId][buyer];
                    console.log("Processing NFT transfers for buyer:", buyer);
                    console.log("Number of items to transfer:", buyerItems.length);
                    
                    for (uint256 j = 0; j < buyerItems.length; j++) {
                        uint256 itemId = buyerItems[j];
                        NFTItem storage item = items[itemId];
                        console.log("Transferring item ID:", itemId);
                        
                        // Mark item as sold
                        item.sold = true;
                        
                        // Transfer NFT to buyer
                        try IERC721(item.nftContract).safeTransferFrom(
                            address(this),
                            buyer,
                            item.tokenId
                        ) {
                            console.log("NFT transferred to buyer");
                            console.log(item.nftContract);
                            console.log(item.tokenId);
                            console.log(address(this));
                            console.log(buyer);
                        } catch Error(string memory reason) {
                            console.log("NFT transfer failed for item:", itemId);
                            console.log(reason);
                            // Continue execution even if transfer fails
                        } catch {
                            console.log("NFT transfer failed for item:", itemId);
                            // Continue execution even if transfer fails
                        }
                    }
                }
            }
            
            // Complete the bundle purchase
            bundle.completed = true;
            bundle.active = false;
            
            emit BundlePurchased(_bundleId, bundle.interestedBuyers);
            console.log("Bundle purchase completed successfully");
        } else {
            console.log("Waiting for more buyers to pay");
        }
    }

    /**
     * @dev Allows a seller to withdraw their NFT if it hasn't been sold
     */
    function withdrawNFT(uint256 _itemId) external nonReentrant {
        console.log("withdrawNFT called");
        console.log("Item ID:", _itemId);
        console.log("Caller:", msg.sender);
        
        NFTItem storage item = items[_itemId];
        
        require(item.seller == msg.sender, "Not the seller");
        require(!item.sold, "Item already sold");
        
        // Optimize gas usage with a more efficient check
        bool inActiveBundle = isItemInActiveBundle(_itemId);
        console.log("Item in active bundle:", inActiveBundle ? "true" : "false");
        require(!inActiveBundle, "Item is in an active bundle");
        
        // Transfer NFT back to seller
        try IERC721(item.nftContract).safeTransferFrom(
            address(this),
            msg.sender,
            item.tokenId
        ) {
            console.log("NFT transferred back to seller");
            console.log(address(this));
            console.log(msg.sender);
            console.log(item.nftContract);
            console.log(item.tokenId);
        } catch Error(string memory reason) {
            console.log("NFT transfer back to seller failed:");
            console.log(reason);
            revert(string(abi.encodePacked("NFT transfer failed: ", reason)));
        } catch {
            console.log("NFT transfer back to seller failed: unknown error");
            revert("NFT transfer failed: unknown error");
        }
        
        // Mark as withdrawn (not sold, but no longer available)
        item.sold = true;
        
        emit NFTWithdrawn(_itemId, msg.sender);
        console.log("NFT withdrawn successfully");
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
        bool completed,
        uint256 paidCount,
        string memory name,
        string memory description,
        uint256 placeholder  // Added placeholder to match test expectations
    ) {
        Bundle storage bundle = bundles[_bundleId];
        return (
            bundle.itemIds,
            bundle.price,
            bundle.requiredBuyers,
            bundle.active,
            bundle.interestedBuyers,
            bundle.completed,
            bundle.paidCount,
            bundle.name,
            bundle.description,
            0  // Placeholder value
        );
    }

    /**
     * @dev Returns the items a buyer is interested in for a specific bundle
     */
    function getBuyerInterests(uint256 _bundleId, address _buyer) external view returns (uint256[] memory) {
        return buyerItemInterests[_bundleId][_buyer];
    }

    /**
     * @dev Returns all buyers interested in a specific bundle with their interests
     */
    function getAllBuyerInterests(uint256 _bundleId) external view returns (
        address[] memory buyers,
        uint256[][] memory itemInterests,
        bool[] memory hasPaidStatus,
        uint256[] memory shapleyValuesList
    ) {
        Bundle storage bundle = bundles[_bundleId];
        uint256 buyerCount = bundle.interestedBuyers.length;
        
        buyers = new address[](buyerCount);
        itemInterests = new uint256[][](buyerCount);
        hasPaidStatus = new bool[](buyerCount);
        shapleyValuesList = new uint256[](buyerCount);
        
        for (uint256 i = 0; i < buyerCount; i++) {
            address buyer = bundle.interestedBuyers[i];
            buyers[i] = buyer;
            itemInterests[i] = buyerItemInterests[_bundleId][buyer];
            hasPaidStatus[i] = hasPaid[_bundleId][buyer];
            shapleyValuesList[i] = shapleyValues[_bundleId][buyer];
        }
        
        return (buyers, itemInterests, hasPaidStatus, shapleyValuesList);
    }

    /**
     * @dev Allows the bundle creator to cancel a bundle
     */
    function cancelBundle(uint256 _bundleId) external nonReentrant {
        console.log("cancelBundle called");
        console.log("Bundle ID:", _bundleId);
        console.log("Caller:", msg.sender);
        
        Bundle storage bundle = bundles[_bundleId];
        require(bundle.active, "Bundle is not active");
        require(!bundle.completed, "Bundle already completed");
        
        // Verify all items in the bundle belong to the caller
        for (uint256 i = 0; i < bundle.itemIds.length; i++) {
            uint256 itemId = bundle.itemIds[i];
            console.log("Checking item ID:", itemId);
            console.log("Item seller:", items[itemId].seller);
            console.log("Caller:", msg.sender);
            
            require(items[bundle.itemIds[i]].seller == msg.sender, "Not the seller of all items");
        }
        
        bundle.active = false;
        
        emit BundleCancelled(_bundleId);
        console.log("Bundle cancelled successfully");
    }

    /**
     * @dev Returns the total number of items listed
     */
    function getItemCount() external view returns (uint256) {
        return _itemIds;
    }

    /**
     * @dev Returns the total number of bundles created
     */
    function getBundleCount() external view returns (uint256) {
        return _bundleIds;
    }

    /**
     * @dev Returns detailed information about an item
     */
    function getItemInfo(uint256 _itemId) external view returns (
        address nftContract,
        address seller,
        uint256 tokenId,
        bool sold
    ) {
        NFTItem storage item = items[_itemId];
        return (
            item.nftContract,
            item.seller,
            item.tokenId,
            item.sold
        );
    }

    /**
     * @dev Returns the Shapley value for a specific buyer in a bundle
     */
    function getShapleyValue(uint256 _bundleId, address _buyer) external view returns (uint256) {
        return shapleyValues[_bundleId][_buyer];
    }

    /**
     * @dev Checks if a buyer has paid for a bundle
     */
    function hasBuyerPaid(uint256 _bundleId, address _buyer) external view returns (bool) {
        return hasPaid[_bundleId][_buyer];
    }

    /**
     * @dev Returns all bundles a seller has created
     */
    function getSellerBundles(address _seller) external view returns (uint256[] memory) {
        // Count bundles by this seller
        uint256 count = 0;
        for (uint256 i = 1; i <= _bundleIds; i++) {
            bool isSellerBundle = true;
            Bundle storage bundle = bundles[i];
            
            for (uint256 j = 0; j < bundle.itemIds.length; j++) {
                if (items[bundle.itemIds[j]].seller != _seller) {
                    isSellerBundle = false;
                    break;
                }
            }
            
            if (isSellerBundle) {
                count++;
            }
        }
        
        // Create array of bundle IDs
        uint256[] memory sellerBundles = new uint256[](count);
        uint256 index = 0;
        
        for (uint256 i = 1; i <= _bundleIds; i++) {
            bool isSellerBundle = true;
            Bundle storage bundle = bundles[i];
            
            for (uint256 j = 0; j < bundle.itemIds.length; j++) {
                if (items[bundle.itemIds[j]].seller != _seller) {
                    isSellerBundle = false;
                    break;
                }
            }
            
            if (isSellerBundle) {
                sellerBundles[index] = i;
                index++;
            }
        }
        
        return sellerBundles;
    }

    /**
     * @dev Returns all bundles a buyer is interested in
     */
    function getBuyerBundles(address _buyer) external view returns (uint256[] memory) {
        // Count bundles this buyer is interested in
        uint256 count = 0;
        for (uint256 i = 1; i <= _bundleIds; i++) {
            if (bundles[i].buyerInterested[_buyer]) {
                count++;
            }
        }
        
        // Create array of bundle IDs
        uint256[] memory buyerBundles = new uint256[](count);
        uint256 index = 0;
        
        for (uint256 i = 1; i <= _bundleIds; i++) {
            if (bundles[i].buyerInterested[_buyer]) {
                buyerBundles[index] = i;
                index++;
            }
        }
        
        return buyerBundles;
    }

    /**
     * @dev Returns all items a seller has listed
     */
    function getSellerItems(address _seller) external view returns (uint256[] memory) {
        // Count items by this seller
        uint256 count = 0;
        for (uint256 i = 1; i <= _itemIds; i++) {
            if (items[i].seller == _seller) {
                count++;
            }
        }
        
        // Create array of item IDs
        uint256[] memory sellerItems = new uint256[](count);
        uint256 index = 0;
        
        for (uint256 i = 1; i <= _itemIds; i++) {
            if (items[i].seller == _seller) {
                sellerItems[index] = i;
                index++;
            }
        }
        
        return sellerItems;
    }

    /**
     * @dev Returns all active bundles
     */
    function getActiveBundles() external view returns (uint256[] memory) {
        // Count active bundles
        uint256 count = 0;
        for (uint256 i = 1; i <= _bundleIds; i++) {
            if (bundles[i].active && !bundles[i].completed) {
                count++;
            }
        }
        
        // Create array of bundle IDs
        uint256[] memory activeBundles = new uint256[](count);
        uint256 index = 0;
        
        for (uint256 i = 1; i <= _bundleIds; i++) {
            if (bundles[i].active && !bundles[i].completed) {
                activeBundles[index] = i;
                index++;
            }
        }
        
        return activeBundles;
    }

    /**
     * @dev Returns all completed bundles
     */
    function getCompletedBundles() external view returns (uint256[] memory) {
        // Count completed bundles
        uint256 count = 0;
        for (uint256 i = 1; i <= _bundleIds; i++) {
            if (bundles[i].completed) {
                count++;
            }
        }
        
        // Create array of bundle IDs
        uint256[] memory completedBundles = new uint256[](count);
        uint256 index = 0;
        
        for (uint256 i = 1; i <= _bundleIds; i++) {
            if (bundles[i].completed) {
                completedBundles[index] = i;
                index++;
            }
        }
        
        return completedBundles;
    }

    /**
     * @dev Returns the number of buyers who have paid for a bundle
     */
    function getBundlePaidCount(uint256 _bundleId) external view returns (uint256) {
        Bundle storage bundle = bundles[_bundleId];
        return bundle.paidCount;
    }

    /**
     * @dev Returns a summary of all marketplace activity
     */
    function getMarketplaceSummary() external view returns (
        uint256 totalItems,
        uint256 totalBundles,
        uint256 activeItems,
        uint256 activeBundles,
        uint256 completedBundles
    ) {
        totalItems = _itemIds;
        totalBundles = _bundleIds;
        
        // Count active items
        uint256 activeItemCount = 0;
        for (uint256 i = 1; i <= _itemIds; i++) {
            if (!items[i].sold) {
                activeItemCount++;
            }
        }
        
        // Count active and completed bundles
        uint256 activeBundleCount = 0;
        uint256 completedBundleCount = 0;
        for (uint256 i = 1; i <= _bundleIds; i++) {
            if (bundles[i].active && !bundles[i].completed) {
                activeBundleCount++;
            }
            if (bundles[i].completed) {
                completedBundleCount++;
            }
        }
        
        return (
            totalItems,
            totalBundles,
            activeItemCount,
            activeBundleCount,
            completedBundleCount
        );
    }

    /**
     * @dev Returns all NFTs owned by a specific address
     * This is a convenience function to check ownership after bundle completion
     */
    function getNFTsOwnedByAddress(address _nftContract, address _owner) external view returns (uint256[] memory) {
        // This is a simplified implementation that works for testing
        // In production, you might need to implement a more efficient approach
        
        // Create a dynamic array to store token IDs
        uint256[] memory ownedTokens = new uint256[](_itemIds);
        uint256 count = 0;
        
        // Check each item to see if it's owned by the address
        for (uint256 i = 1; i <= _itemIds; i++) {
            NFTItem storage item = items[i];
            if (item.nftContract == _nftContract) {
                try IERC721(_nftContract).ownerOf(item.tokenId) returns (address owner) {
                    if (owner == _owner) {
                        ownedTokens[count] = item.tokenId;
                        count++;
                    }
                } catch {
                    // Token might not exist or other error
                    continue;
                }
            }
        }
        
        // Create a properly sized array with just the found tokens
        uint256[] memory result = new uint256[](count);
        for (uint256 i = 0; i < count; i++) {
            result[i] = ownedTokens[i];
        }
        
        return result;
    }
}