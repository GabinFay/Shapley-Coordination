// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title MockERC721
 * @dev A simple ERC721 contract for testing purposes
 */
contract MockERC721 is ERC721, Ownable {
    // Counter to track the total number of tokens
    uint256 private _totalSupply;
    
    // Mapping from token ID to token URI
    mapping(uint256 => string) private _tokenURIs;

    constructor(string memory name, string memory symbol) 
        ERC721(name, symbol) 
        Ownable(msg.sender) 
    {}

    /**
     * @dev Mints a new token
     * @param to The address that will receive the minted token
     * @param tokenId The token id to mint
     * @param uri The token URI
     */
    function mint(address to, uint256 tokenId, string memory uri) external onlyOwner {
        _safeMint(to, tokenId);
        _tokenURIs[tokenId] = uri;
        _totalSupply++;
    }

    /**
     * @dev Returns the total number of tokens minted
     */
    function totalSupply() external view returns (uint256) {
        return _totalSupply;
    }
    
    /**
     * @dev Returns the URI for a given token ID
     * @param tokenId The token ID to query
     * @return The token URI
     */
    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        // Check if the token exists
        require(_ownerOf(tokenId) != address(0), "ERC721Metadata: URI query for nonexistent token");
        
        string memory _tokenURI = _tokenURIs[tokenId];
        
        // If there is no token URI, return the empty string
        if (bytes(_tokenURI).length == 0) {
            return super.tokenURI(tokenId);
        }
        
        return _tokenURI;
    }
} 