// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title MockERC721
 * @dev A simple ERC721 contract for testing purposes
 */
contract MockERC721 is ERC721, Ownable {
    constructor(string memory name, string memory symbol) 
        ERC721(name, symbol) 
        Ownable(msg.sender) 
    {}

    /**
     * @dev Mints a new token
     * @param to The address that will receive the minted token
     * @param tokenId The token id to mint
     * @param tokenURI The token URI
     */
    function mint(address to, uint256 tokenId, string memory tokenURI) external onlyOwner {
        _safeMint(to, tokenId);
    }
} 