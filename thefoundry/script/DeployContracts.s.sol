// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Script.sol";
import "../src/NFTBundleMarket.sol";
import "../src/MockERC721.sol";

contract DeployContracts is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        // Deploy NFTBundleMarket
        NFTBundleMarket nftBundleMarket = new NFTBundleMarket();
        
        // Deploy MockERC721
        MockERC721 mockNFT = new MockERC721("MockNFT", "MNFT");

        vm.stopBroadcast();

        // Log the deployed contract addresses
        console.log("NFTBundleMarket deployed at:", address(nftBundleMarket));
        console.log("MockERC721 deployed at:", address(mockNFT));
    }
} 