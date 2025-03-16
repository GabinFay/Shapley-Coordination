// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";
import "../src/NFTBundleMarket.sol";
import "./mocks/MockNFT.sol";

contract NFTBundleMarketTest is Test {
    NFTBundleMarket public market;
    MockNFT public nft;
    
    address public seller;
    address public buyer1;
    address public buyer2;
    address public buyer3;
    address public teeWallet;
    
    uint256 public constant BUNDLE_PRICE = 3 ether;
    
    function setUp() public {
        // Deploy the marketplace contract
        market = new NFTBundleMarket();
        
        // Deploy a mock NFT contract for testing
        nft = new MockNFT("TestNFT", "TNFT");
        
        // Set up test accounts
        seller = makeAddr("seller");
        buyer1 = makeAddr("buyer1");
        buyer2 = makeAddr("buyer2");
        buyer3 = makeAddr("buyer3");
        teeWallet = makeAddr("teeWallet");
        
        // Fund accounts
        vm.deal(seller, 10 ether);
        vm.deal(buyer1, 10 ether);
        vm.deal(buyer2, 10 ether);
        vm.deal(buyer3, 10 ether);
        
        // Mint NFTs to seller
        vm.startPrank(seller);
        nft.mint(seller, 1);
        nft.mint(seller, 2);
        nft.mint(seller, 3);
        vm.stopPrank();
        
        // Set the TEE wallet address
        vm.prank(address(this));
        market.setShapleyCalculator(teeWallet);
    }
    
    function testFullBundleLifecycle() public {
        // Step 1: Seller lists NFTs
        vm.startPrank(seller);
        nft.setApprovalForAll(address(market), true);
        
        uint256 item1 = market.listNFT(address(nft), 1);
        uint256 item2 = market.listNFT(address(nft), 2);
        uint256 item3 = market.listNFT(address(nft), 3);
        
        // Step 2: Seller creates a bundle
        uint256[] memory itemIds = new uint256[](3);
        itemIds[0] = item1;
        itemIds[1] = item2;
        itemIds[2] = item3;
        
        uint256 bundleId = market.createBundle(itemIds, BUNDLE_PRICE, 3);
        vm.stopPrank();
        
        // Verify bundle was created
        (
            uint256[] memory bundleItems,
            uint256 price,
            uint256 requiredBuyers,
            bool active,
            ,
            bool completed,
            ,
            ,
            ,
            uint256 placeholder
        ) = market.getBundleInfo(bundleId);
        
        assertEq(bundleItems.length, 3);
        assertEq(bundleItems[0], item1);
        assertEq(bundleItems[1], item2);
        assertEq(bundleItems[2], item3);
        assertEq(price, BUNDLE_PRICE);
        assertEq(requiredBuyers, 3);
        assertTrue(active);
        assertFalse(completed);
        
        // Step 3: Buyers express interest
        uint256[] memory buyer1Items = new uint256[](1);
        buyer1Items[0] = item1;
        
        uint256[] memory buyer2Items = new uint256[](1);
        buyer2Items[0] = item2;
        
        uint256[] memory buyer3Items = new uint256[](1);
        buyer3Items[0] = item3;
        
        vm.prank(buyer1);
        market.expressInterest(bundleId, buyer1Items);
        
        vm.prank(buyer2);
        market.expressInterest(bundleId, buyer2Items);
        
        // Verify that bundle is not ready yet (only 2 buyers)
        (
            ,
            ,
            ,
            ,
            address[] memory interestedBuyers,
            ,
            ,
            ,
            ,
            uint256 placeholder1
        ) = market.getBundleInfo(bundleId);
        
        assertEq(interestedBuyers.length, 2);
        
        // Third buyer expresses interest
        vm.prank(buyer3);
        market.expressInterest(bundleId, buyer3Items);
        
        // Verify that bundle is now ready
        (
            ,
            ,
            ,
            ,
            address[] memory updatedBuyers,
            ,
            ,
            ,
            ,
            uint256 placeholder2
        ) = market.getBundleInfo(bundleId);
        
        assertEq(updatedBuyers.length, 3);
        
        // Step 4: Request attestation for Shapley value calculation
        vm.prank(buyer1);
        market.requestAttestation(bundleId);
        
        // Step 5: TEE sets Shapley values
        address[] memory buyers = new address[](3);
        buyers[0] = buyer1;
        buyers[1] = buyer2;
        buyers[2] = buyer3;
        
        uint256[] memory values = new uint256[](3);
        values[0] = 1 ether;  // Shapley value for buyer1
        values[1] = 1 ether;  // Shapley value for buyer2
        values[2] = 1 ether;  // Shapley value for buyer3
        
        vm.prank(teeWallet);
        market.setShapleyValues(bundleId, buyers, values);
        
        // Verify Shapley values were set correctly
        assertEq(market.getShapleyValue(bundleId, buyer1), 1 ether);
        assertEq(market.getShapleyValue(bundleId, buyer2), 1 ether);
        assertEq(market.getShapleyValue(bundleId, buyer3), 1 ether);
        
        // Step 6: Buyers complete purchase
        uint256 buyer1BalanceBefore = buyer1.balance;
        uint256 buyer2BalanceBefore = buyer2.balance;
        uint256 buyer3BalanceBefore = buyer3.balance;
        uint256 sellerBalanceBefore = seller.balance;
        
        vm.prank(buyer1);
        market.completeBundlePurchase{value: 1 ether}(bundleId);
        
        vm.prank(buyer2);
        market.completeBundlePurchase{value: 1 ether}(bundleId);
        
        // Verify that bundle is not completed yet (only 2 buyers paid)
        (
            ,
            ,
            ,
            ,
            ,
            bool bundleCompleted,
            uint256 paidCount,
            ,
            ,
            uint256 placeholder3
        ) = market.getBundleInfo(bundleId);
        
        assertFalse(bundleCompleted);
        assertEq(paidCount, 2);
        
        // Third buyer completes purchase
        vm.prank(buyer3);
        market.completeBundlePurchase{value: 1 ether}(bundleId);
        
        // Verify that bundle is now completed
        (
            ,
            ,
            ,
            bool bundleActive,
            ,
            bool bundleNowCompleted,
            ,
            ,
            ,
            uint256 placeholder4
        ) = market.getBundleInfo(bundleId);
        
        assertFalse(bundleActive);
        assertTrue(bundleNowCompleted);
        
        // Verify buyer balances decreased
        assertEq(buyer1.balance, buyer1BalanceBefore - 1 ether);
        assertEq(buyer2.balance, buyer2BalanceBefore - 1 ether);
        assertEq(buyer3.balance, buyer3BalanceBefore - 1 ether);
        
        // Verify seller balance increased (should get the full bundle price)
        assertEq(seller.balance, sellerBalanceBefore + BUNDLE_PRICE);
        
        // Verify NFT ownership transferred
        assertEq(nft.ownerOf(1), buyer1);
        assertEq(nft.ownerOf(2), buyer2);
        assertEq(nft.ownerOf(3), buyer3);
    }
    
    function testWithdrawNFT() public {
        // Seller lists an NFT
        vm.startPrank(seller);
        nft.setApprovalForAll(address(market), true);
        uint256 itemId = market.listNFT(address(nft), 1);
        
        // Verify NFT is now owned by the marketplace
        assertEq(nft.ownerOf(1), address(market));
        
        // Seller withdraws the NFT
        market.withdrawNFT(itemId);
        vm.stopPrank();
        
        // Verify NFT is back with the seller
        assertEq(nft.ownerOf(1), seller);
        
        // Verify item is marked as sold (withdrawn)
        (, , , bool sold) = market.getItemInfo(itemId);
        assertTrue(sold);
    }
    
    function testCancelBundle() public {
        // Seller lists NFTs and creates a bundle
        vm.startPrank(seller);
        nft.setApprovalForAll(address(market), true);
        
        uint256 item1 = market.listNFT(address(nft), 1);
        uint256 item2 = market.listNFT(address(nft), 2);
        
        uint256[] memory itemIds = new uint256[](2);
        itemIds[0] = item1;
        itemIds[1] = item2;
        
        uint256 bundleId = market.createBundle(itemIds, 2 ether, 2);
        
        // Seller cancels the bundle
        market.cancelBundle(bundleId);
        vm.stopPrank();
        
        // Verify bundle is no longer active
        (
            ,
            ,
            ,
            bool active,
            ,
            ,
            ,
            ,
            ,
            uint256 placeholder5
        ) = market.getBundleInfo(bundleId);
        
        assertFalse(active);
    }
    
    function testCannotWithdrawNFTInActiveBundle() public {
        // Seller lists NFTs and creates a bundle
        vm.startPrank(seller);
        nft.setApprovalForAll(address(market), true);
        
        uint256 item1 = market.listNFT(address(nft), 1);
        
        uint256[] memory itemIds = new uint256[](1);
        itemIds[0] = item1;
        
        market.createBundle(itemIds, 1 ether, 1);
        
        // Attempt to withdraw NFT that's in an active bundle should fail
        vm.expectRevert("Item is in an active bundle");
        market.withdrawNFT(item1);
        vm.stopPrank();
    }
    
    function testExcessPaymentRefund() public {
        // Set up a bundle with one buyer
        vm.startPrank(seller);
        nft.setApprovalForAll(address(market), true);
        uint256 itemId = market.listNFT(address(nft), 1);
        
        uint256[] memory itemIds = new uint256[](1);
        itemIds[0] = itemId;
        
        uint256 bundleId = market.createBundle(itemIds, 1 ether, 1);
        vm.stopPrank();
        
        // Buyer expresses interest
        uint256[] memory buyerItems = new uint256[](1);
        buyerItems[0] = itemId;
        
        vm.prank(buyer1);
        market.expressInterest(bundleId, buyerItems);
        
        // TEE sets Shapley values
        address[] memory buyers = new address[](1);
        buyers[0] = buyer1;
        
        uint256[] memory values = new uint256[](1);
        values[0] = 1 ether;
        
        vm.prank(teeWallet);
        market.setShapleyValues(bundleId, buyers, values);
        
        // Buyer pays more than required
        uint256 buyerBalanceBefore = buyer1.balance;
        
        vm.prank(buyer1);
        market.completeBundlePurchase{value: 2 ether}(bundleId);
        
        // Verify buyer was refunded the excess
        assertEq(buyer1.balance, buyerBalanceBefore - 1 ether);
    }
    
    function testUnauthorizedShapleyValueSetting() public {
        // Set up a bundle
        vm.startPrank(seller);
        nft.setApprovalForAll(address(market), true);
        uint256 itemId = market.listNFT(address(nft), 1);
        
        uint256[] memory itemIds = new uint256[](1);
        itemIds[0] = itemId;
        
        uint256 bundleId = market.createBundle(itemIds, 1 ether, 1);
        vm.stopPrank();
        
        // Buyer expresses interest
        uint256[] memory buyerItems = new uint256[](1);
        buyerItems[0] = itemId;
        
        vm.prank(buyer1);
        market.expressInterest(bundleId, buyerItems);
        
        // Unauthorized account tries to set Shapley values
        address[] memory buyers = new address[](1);
        buyers[0] = buyer1;
        
        uint256[] memory values = new uint256[](1);
        values[0] = 1 ether;
        
        vm.prank(buyer2); // Not the TEE wallet
        vm.expectRevert("Not authorized");
        market.setShapleyValues(bundleId, buyers, values);
    }
} 