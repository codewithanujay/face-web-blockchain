// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ContentRegistry {
    struct Record {
        bytes32 contentHash;
        string sourceUrl;
        uint256 timestamp;
        address submitter;
    }

    uint256 public nextId;
    mapping(uint256 => Record) public records;

    event ContentRegistered(uint256 indexed id, bytes32 indexed contentHash, string sourceUrl, uint256 timestamp, address indexed submitter);

    function registerContent(bytes32 contentHash, string calldata sourceUrl) external returns (uint256 id) {
        id = nextId++;
        records[id] = Record(contentHash, sourceUrl, block.timestamp, msg.sender);
        emit ContentRegistered(id, contentHash, sourceUrl, block.timestamp, msg.sender);
    }

    function getRecord(uint256 id) external view returns (bytes32, string memory, uint256, address) {
        Record memory r = records[id];
        return (r.contentHash, r.sourceUrl, r.timestamp, r.submitter);
    }
}
