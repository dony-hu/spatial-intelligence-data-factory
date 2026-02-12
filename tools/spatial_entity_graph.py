"""
Spatial Entity Relationship Graph - Core graph structure and relationship extraction
"""

import uuid
import json
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import math


class EntityNodeType(Enum):
    """Entity node types in the graph"""
    PROVINCE = "province"
    CITY = "city"
    DISTRICT = "district"
    STREET = "street"
    LANE = "lane"
    BUILDING = "building"
    POI = "poi"
    LANDMARK = "landmark"
    ADDRESS = "address"
    FUSION_ENTITY = "fusion_entity"


class RelationshipType(Enum):
    """Relationship types in the graph"""
    HIERARCHICAL = "hierarchical"              # 层级关系 (e.g., 市->区->街道)
    SPATIAL_CONTAINS = "spatial_contains"      # 空间包含 (e.g., 区包含街道)
    SPATIAL_ADJACENT = "spatial_adjacent"      # 相邻关系
    SPATIAL_NEAR = "spatial_near"              # 近邻关系 (距离<100m)
    ENTITY_MAPPING = "entity_mapping"          # 地址->实体映射
    MULTI_SOURCE_FUSION = "multi_source_fusion" # 多源融合
    DATA_LINEAGE = "data_lineage"              # 数据血缘


@dataclass
class EntityNode:
    """Represents a node in the entity relationship graph"""
    node_id: str
    node_type: EntityNodeType
    name: str
    level: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    confidence: float = 1.0
    metadata: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "level": self.level,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class EntityRelationship:
    """Represents a relationship (edge) in the graph"""
    relationship_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: RelationshipType
    confidence: float = 1.0
    metadata: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "relationship_id": self.relationship_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "relationship_type": self.relationship_type.value,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


class SpatialEntityGraph:
    """Spatial entity relationship graph manager"""

    def __init__(self, region: str = "Shanghai"):
        self.region = region
        self.nodes: Dict[str, EntityNode] = {}
        self.relationships: Dict[str, EntityRelationship] = {}
        self.node_by_name: Dict[str, List[str]] = {}  # Index for name lookup

    def add_node(self, node: EntityNode) -> str:
        """Add a node to the graph"""
        self.nodes[node.node_id] = node

        # Update name index
        if node.name not in self.node_by_name:
            self.node_by_name[node.name] = []
        self.node_by_name[node.name].append(node.node_id)

        return node.node_id

    def add_relationship(self, relationship: EntityRelationship) -> str:
        """Add a relationship to the graph"""
        if relationship.source_node_id not in self.nodes:
            raise ValueError(f"Source node {relationship.source_node_id} not found")
        if relationship.target_node_id not in self.nodes:
            raise ValueError(f"Target node {relationship.target_node_id} not found")

        self.relationships[relationship.relationship_id] = relationship
        return relationship.relationship_id

    def get_node(self, node_id: str) -> Optional[EntityNode]:
        """Get a node by ID"""
        return self.nodes.get(node_id)

    def get_nodes_by_type(self, node_type: EntityNodeType) -> List[EntityNode]:
        """Get all nodes of a specific type"""
        return [node for node in self.nodes.values() if node.node_type == node_type]

    def get_relationships_by_type(self, rel_type: RelationshipType) -> List[EntityRelationship]:
        """Get all relationships of a specific type"""
        return [rel for rel in self.relationships.values() if rel.relationship_type == rel_type]

    def get_node_relationships(self, node_id: str) -> Tuple[List[EntityRelationship], List[EntityRelationship]]:
        """Get incoming and outgoing relationships for a node"""
        outgoing = [rel for rel in self.relationships.values() if rel.source_node_id == node_id]
        incoming = [rel for rel in self.relationships.values() if rel.target_node_id == node_id]
        return incoming, outgoing

    def create_hierarchical_node(self, code: str, name: str, level: int) -> str:
        """Create a hierarchical node (province/city/district/street)"""
        node_id = f"admin_{code}"
        node_type_map = {
            1: EntityNodeType.PROVINCE,
            2: EntityNodeType.CITY,
            3: EntityNodeType.DISTRICT,
            4: EntityNodeType.STREET,
            5: EntityNodeType.LANE
        }
        node_type = node_type_map.get(level, EntityNodeType.STREET)

        node = EntityNode(
            node_id=node_id,
            node_type=node_type,
            name=name,
            level=level,
            confidence=1.0
        )
        return self.add_node(node)

    def create_address_node(self, standardized_id: str, full_address: str,
                           latitude: float, longitude: float, confidence: float) -> str:
        """Create an address node"""
        node_id = f"addr_{standardized_id}"
        node = EntityNode(
            node_id=node_id,
            node_type=EntityNodeType.ADDRESS,
            name=full_address,
            latitude=latitude,
            longitude=longitude,
            confidence=confidence
        )
        return self.add_node(node)

    def create_poi_node(self, entity_id: str, entity_name: str,
                       latitude: Optional[float], longitude: Optional[float],
                       confidence: float) -> str:
        """Create a POI entity node"""
        node_id = f"poi_{entity_id}"
        node = EntityNode(
            node_id=node_id,
            node_type=EntityNodeType.POI,
            name=entity_name,
            latitude=latitude,
            longitude=longitude,
            confidence=confidence
        )
        return self.add_node(node)

    def add_hierarchical_relationship(self, parent_code: str, child_code: str) -> str:
        """Add hierarchical relationship (parent -> child)"""
        parent_id = f"admin_{parent_code}"
        child_id = f"admin_{child_code}"
        rel_id = f"rel_hier_{parent_code}_{child_code}"

        relationship = EntityRelationship(
            relationship_id=rel_id,
            source_node_id=parent_id,
            target_node_id=child_id,
            relationship_type=RelationshipType.HIERARCHICAL,
            confidence=1.0,
            metadata={"direction": "parent_to_child"}
        )
        return self.add_relationship(relationship)

    def add_spatial_relationship(self, source_id: str, target_id: str,
                                rel_type: RelationshipType, confidence: float = 1.0) -> str:
        """Add spatial relationship (contains, adjacent, near)"""
        rel_id = f"rel_spatial_{source_id}_{target_id}_{rel_type.value}"

        relationship = EntityRelationship(
            relationship_id=rel_id,
            source_node_id=source_id,
            target_node_id=target_id,
            relationship_type=rel_type,
            confidence=confidence
        )
        return self.add_relationship(relationship)

    def add_mapping_relationship(self, address_node_id: str, entity_node_id: str,
                                confidence: float = 1.0) -> str:
        """Add address to entity mapping relationship"""
        rel_id = f"rel_map_{address_node_id}_{entity_node_id}"

        relationship = EntityRelationship(
            relationship_id=rel_id,
            source_node_id=address_node_id,
            target_node_id=entity_node_id,
            relationship_type=RelationshipType.ENTITY_MAPPING,
            confidence=confidence
        )
        return self.add_relationship(relationship)

    def add_lineage_relationship(self, source_id: str, target_id: str) -> str:
        """Add data lineage relationship (raw -> parsed -> standardized)"""
        rel_id = f"rel_lineage_{source_id}_{target_id}"

        relationship = EntityRelationship(
            relationship_id=rel_id,
            source_node_id=source_id,
            target_node_id=target_id,
            relationship_type=RelationshipType.DATA_LINEAGE,
            confidence=1.0
        )
        return self.add_relationship(relationship)

    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates (in degrees, approximate)"""
        return math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)

    def add_proximity_relationships(self, max_distance: float = 0.01):
        """Add spatial near relationships based on coordinate proximity"""
        address_nodes = self.get_nodes_by_type(EntityNodeType.ADDRESS)

        for i, node1 in enumerate(address_nodes):
            if node1.latitude is None or node1.longitude is None:
                continue

            for node2 in address_nodes[i+1:]:
                if node2.latitude is None or node2.longitude is None:
                    continue

                distance = self.calculate_distance(
                    node1.latitude, node1.longitude,
                    node2.latitude, node2.longitude
                )

                if 0 < distance <= max_distance:
                    rel_id = f"rel_near_{node1.node_id}_{node2.node_id}"
                    confidence = max(0, 1.0 - (distance / max_distance))

                    relationship = EntityRelationship(
                        relationship_id=rel_id,
                        source_node_id=node1.node_id,
                        target_node_id=node2.node_id,
                        relationship_type=RelationshipType.SPATIAL_NEAR,
                        confidence=confidence
                    )
                    self.add_relationship(relationship)

    def get_graph_stats(self) -> Dict:
        """Get graph statistics"""
        rel_type_counts = {}
        for rel_type in RelationshipType:
            rel_type_counts[rel_type.value] = len(self.get_relationships_by_type(rel_type))

        node_type_counts = {}
        for node_type in EntityNodeType:
            node_type_counts[node_type.value] = len(self.get_nodes_by_type(node_type))

        return {
            "total_nodes": len(self.nodes),
            "total_relationships": len(self.relationships),
            "node_types": node_type_counts,
            "relationship_types": rel_type_counts,
            "region": self.region,
            "created_at": datetime.utcnow().isoformat()
        }

    def to_json(self) -> Dict:
        """Export graph as JSON (nodes and edges)"""
        return {
            "metadata": {
                "region": self.region,
                "timestamp": datetime.utcnow().isoformat(),
                "statistics": self.get_graph_stats()
            },
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [rel.to_dict() for rel in self.relationships.values()]
        }

    def to_graphml(self) -> str:
        """Export graph as GraphML format (for Gephi, Neo4j import)"""
        graphml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        graphml += '<graphml xmlns="http://graphml.graphdrawing.org/xmlformat/graphml-1.1rc1.xsd">\n'
        graphml += f'  <graph id="entity_relationship_graph" edgedefault="directed">\n'

        # Define node attributes
        graphml += '    <key id="type" for="node" attr.name="type" attr.type="string"/>\n'
        graphml += '    <key id="name" for="node" attr.name="name" attr.type="string"/>\n'
        graphml += '    <key id="level" for="node" attr.name="level" attr.type="int"/>\n'
        graphml += '    <key id="latitude" for="node" attr.name="latitude" attr.type="double"/>\n'
        graphml += '    <key id="longitude" for="node" attr.name="longitude" attr.type="double"/>\n'
        graphml += '    <key id="confidence" for="node" attr.name="confidence" attr.type="double"/>\n'

        # Define edge attributes
        graphml += '    <key id="rel_type" for="edge" attr.name="type" attr.type="string"/>\n'
        graphml += '    <key id="rel_confidence" for="edge" attr.name="confidence" attr.type="double"/>\n'

        # Add nodes
        for node in self.nodes.values():
            graphml += f'    <node id="{node.node_id}">\n'
            graphml += f'      <data key="type">{node.node_type.value}</data>\n'
            graphml += f'      <data key="name">{node.name}</data>\n'
            if node.level is not None:
                graphml += f'      <data key="level">{node.level}</data>\n'
            if node.latitude is not None:
                graphml += f'      <data key="latitude">{node.latitude}</data>\n'
            if node.longitude is not None:
                graphml += f'      <data key="longitude">{node.longitude}</data>\n'
            graphml += f'      <data key="confidence">{node.confidence}</data>\n'
            graphml += '    </node>\n'

        # Add edges
        for i, rel in enumerate(self.relationships.values()):
            graphml += f'    <edge id="e{i}" source="{rel.source_node_id}" target="{rel.target_node_id}">\n'
            graphml += f'      <data key="rel_type">{rel.relationship_type.value}</data>\n'
            graphml += f'      <data key="rel_confidence">{rel.confidence}</data>\n'
            graphml += '    </edge>\n'

        graphml += '  </graph>\n'
        graphml += '</graphml>\n'

        return graphml
