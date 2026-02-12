"""
Main pipeline for building spatial entity relationship graph
Integrates database, address processing, and visualization
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.init_sqlite import SQLiteInitializer
from database.sqlite_adapter import SQLiteAdapter
from tools.spatial_entity_graph import SpatialEntityGraph, EntityNodeType, RelationshipType
from tools.graph_visualizer import GraphVisualizer
from tools.address_governance import AddressGovernanceSystem
from testdata.address_samples_50 import get_shanghai_samples


def initialize_database():
    """Step 1: Initialize SQLite database"""
    print("\n" + "="*70)
    print("STEP 1: Initialize SQLite Database")
    print("="*70)

    initializer = SQLiteInitializer()
    db_path = initializer.initialize()
    return db_path


def load_sample_addresses(adapter: SQLiteAdapter):
    """Step 2: Load sample address data into database"""
    print("\n" + "="*70)
    print("STEP 2: Load Sample Address Data")
    print("="*70)

    samples = get_shanghai_samples()
    print(f"Loading {len(samples)} address samples from testdata...")

    for i, sample in enumerate(samples, 1):
        try:
            # Insert raw input
            adapter.insert_raw_address(
                input_id=sample["input_id"],
                raw_address=sample["raw_address"],
                source=sample["source"],
                region="Shanghai",
                status="raw",
                confidence=0.9
            )

            # Insert parsed address
            adapter.insert_parsed_address(
                parsed_id=sample["parsed_id"],
                input_id=sample["input_id"],
                province="上海",
                city="上海市",
                district=sample["district"],
                street=sample["street"],
                building=sample["building"],
                unit=sample.get("unit", ""),
                floor=sample.get("floor", ""),
                room=sample.get("room", ""),
                poi_name=sample.get("poi_name", ""),
                poi_category=sample.get("poi_category", ""),
                region="Shanghai"
            )

            # Insert standardized address
            adapter.insert_standardized_address(
                standardized_id=sample["standardized_id"],
                parsed_id=sample["parsed_id"],
                standard_full_address=sample["standard_full_address"],
                coordinate_x=sample["lat"],
                coordinate_y=sample["lon"],
                confidence=0.95,
                region="Shanghai",
                province="上海",
                city="上海市",
                district=sample["district"],
                street=sample["street"],
                building=sample["building"]
            )

            # Insert entity mapping
            if sample.get("entity_name"):
                adapter.insert_entity_mapping(
                    mapping_id=f"map_{sample['standardized_id']}",
                    standardized_id=sample["standardized_id"],
                    entity_id=f"entity_{sample['standardized_id']}",
                    entity_type=sample.get("entity_type", "poi"),
                    entity_name=sample["entity_name"],
                    similarity_score=0.95,
                    region="Shanghai"
                )

            if i % 10 == 0:
                print(f"  ✓ Loaded {i}/{len(samples)} addresses")

        except Exception as e:
            print(f"  ✗ Error loading sample {i}: {e}")

    print(f"✓ Loaded {len(samples)} address records")
    return len(samples)


def extract_admin_divisions(adapter: SQLiteAdapter, graph: SpatialEntityGraph):
    """Extract administrative divisions and create nodes"""
    print("\n" + "="*70)
    print("STEP 3: Extract Administrative Divisions")
    print("="*70)

    # Define Shanghai administrative hierarchy
    admin_divisions = [
        # Province level
        ("3100", "上海", 1, None),
        # City level (Shanghai is province-level city)
        ("3101", "上海市", 2, "3100"),
        # District level
        ("310101", "黄浦区", 3, "3101"),
        ("310115", "浦东新区", 3, "3101"),
        ("310104", "徐汇区", 3, "3101"),
        ("310106", "静安区", 3, "3101"),
        ("310109", "虹口区", 3, "3101"),
        ("310110", "杨浦区", 3, "3101"),
        ("310112", "闵行区", 3, "3101"),
        ("310113", "宝山区", 3, "3101"),
        ("310114", "嘉定区", 3, "3101"),
        ("310120", "奉贤区", 3, "3101"),
    ]

    for code, name, level, parent_code in admin_divisions:
        adapter.insert_admin_division(
            code=code,
            name=name,
            level=level,
            parent_code=parent_code,
            region="Shanghai"
        )

        # Add to graph
        graph.create_hierarchical_node(code, name, level)

    print(f"✓ Extracted {len(admin_divisions)} administrative divisions")
    return admin_divisions


def build_entity_graph(adapter: SQLiteAdapter, graph: SpatialEntityGraph, num_addresses: int):
    """Step 3: Build entity relationship graph"""
    print("\n" + "="*70)
    print("STEP 4: Build Entity Relationship Graph")
    print("="*70)

    # Get standardized addresses from database
    addresses = adapter.get_standardized_addresses_by_region("Shanghai")
    print(f"Processing {len(addresses)} standardized addresses...")

    # Create address nodes
    for addr in addresses:
        if addr["coordinate_x"] and addr["coordinate_y"]:
            graph.create_address_node(
                standardized_id=addr["standardized_id"],
                full_address=addr["standard_full_address"],
                latitude=addr["coordinate_x"],
                longitude=addr["coordinate_y"],
                confidence=addr["confidence_score"]
            )

    print(f"✓ Created {len(addresses)} address nodes")

    # Create POI nodes from entity mappings
    # (Simplified: create basic POI nodes for entities)
    samples = get_shanghai_samples()
    poi_count = 0
    for sample in samples:
        if sample.get("entity_name"):
            poi_count += 1
            graph.create_poi_node(
                entity_id=sample["standardized_id"],
                entity_name=sample["entity_name"],
                latitude=sample["lat"],
                longitude=sample["lon"],
                confidence=0.9
            )

    print(f"✓ Created {poi_count} POI nodes")

    # Extract hierarchical relationships (admin division hierarchy)
    print("Extracting hierarchical relationships...")
    admin_rels = 0
    admin_divisions = adapter.get_admin_divisions_by_region("Shanghai")
    for admin in admin_divisions:
        if admin["parent_code"]:
            graph.add_hierarchical_relationship(
                parent_code=admin["parent_code"],
                child_code=admin["code"]
            )
            admin_rels += 1

    print(f"✓ Created {admin_rels} hierarchical relationships")

    # Extract spatial relationships (addresses to districts)
    print("Extracting spatial relationships...")
    spatial_rels = 0
    for addr in addresses:
        district_name = addr["standard_district"]
        # Find district node
        district_nodes = graph.get_nodes_by_type(EntityNodeType.DISTRICT)
        for dnode in district_nodes:
            if district_name in dnode.name:
                # Add contains relationship
                addr_node_id = f"addr_{addr['standardized_id']}"
                rel_id = f"rel_contains_{dnode.node_id}_{addr_node_id}"
                try:
                    graph.add_spatial_relationship(
                        source_id=dnode.node_id,
                        target_id=addr_node_id,
                        rel_type=RelationshipType.SPATIAL_CONTAINS,
                        confidence=1.0
                    )
                    spatial_rels += 1
                except:
                    pass
                break

    print(f"✓ Created {spatial_rels} spatial contains relationships")

    # Extract entity mapping relationships
    print("Extracting entity mapping relationships...")
    mapping_rels = 0
    for sample in samples:
        addr_node_id = f"addr_{sample['standardized_id']}"
        poi_node_id = f"poi_{sample['standardized_id']}"

        try:
            graph.add_mapping_relationship(
                address_node_id=addr_node_id,
                entity_node_id=poi_node_id,
                confidence=0.95
            )
            mapping_rels += 1
        except:
            pass

    print(f"✓ Created {mapping_rels} entity mapping relationships")

    # Extract proximity relationships
    print("Extracting proximity relationships...")
    graph.add_proximity_relationships(max_distance=0.01)  # ~1km in degrees
    near_rels = len(graph.get_relationships_by_type(RelationshipType.SPATIAL_NEAR))
    print(f"✓ Created {near_rels} proximity relationships")

    return graph


def export_outputs(graph: SpatialEntityGraph):
    """Step 4: Export graph in multiple formats"""
    print("\n" + "="*70)
    print("STEP 5: Export Graph Outputs")
    print("="*70)

    os.makedirs("output", exist_ok=True)

    # Export JSON
    print("Exporting JSON format...")
    json_file = "output/graph.json"
    graph_json = graph.to_json()
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(graph_json, f, ensure_ascii=False, indent=2)
    print(f"✓ JSON exported to {json_file}")

    # Export GraphML
    print("Exporting GraphML format...")
    graphml_file = "output/graph.graphml"
    graphml_content = graph.to_graphml()
    with open(graphml_file, "w", encoding="utf-8") as f:
        f.write(graphml_content)
    print(f"✓ GraphML exported to {graphml_file}")

    # Generate HTML visualization
    print("Generating HTML visualization...")
    visualizer = GraphVisualizer(graph)
    html_file = visualizer.generate_html()
    print(f"✓ HTML visualization generated at {html_file}")

    return {
        "json": json_file,
        "graphml": graphml_file,
        "html": html_file
    }


def print_statistics(graph: SpatialEntityGraph):
    """Print final statistics"""
    print("\n" + "="*70)
    print("FINAL STATISTICS")
    print("="*70)

    stats = graph.get_graph_stats()

    print(f"\n📊 Graph Summary:")
    print(f"  Total Nodes: {stats['total_nodes']}")
    print(f"  Total Edges: {stats['total_relationships']}")
    print(f"  Region: {stats['region']}")

    print(f"\n📍 Node Types:")
    for node_type, count in stats['node_types'].items():
        if count > 0:
            print(f"  • {node_type}: {count}")

    print(f"\n🔗 Relationship Types:")
    for rel_type, count in stats['relationship_types'].items():
        if count > 0:
            print(f"  • {rel_type}: {count}")


def main():
    """Main execution pipeline"""
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*15 + "Spatial Entity Relationship Graph Builder" + " "*11 + "║")
    print("╚" + "="*68 + "╝")

    try:
        # Step 1: Initialize database
        db_path = initialize_database()

        # Step 2: Connect to database
        adapter = SQLiteAdapter(db_path)
        print("\nCleaning previous graph data for idempotent rebuild...")
        adapter.clear_all_data()
        print("✓ Previous data cleared")

        # Step 3: Load sample data
        num_addresses = load_sample_addresses(adapter)

        # Step 4: Extract admin divisions
        admin_divs = extract_admin_divisions(adapter, SpatialEntityGraph("Shanghai"))

        # Initialize empty graph for building
        graph = SpatialEntityGraph("Shanghai")

        # Recreate admin nodes in graph
        for code, name, level, parent_code in admin_divs:
            graph.create_hierarchical_node(code, name, level)

        # Add admin hierarchy relationships
        for code, name, level, parent_code in admin_divs:
            if parent_code:
                graph.add_hierarchical_relationship(parent_code, code)

        # Step 5: Build full entity graph
        graph = build_entity_graph(adapter, graph, num_addresses)

        # Step 6: Export outputs
        outputs = export_outputs(graph)

        # Print statistics
        print_statistics(graph)

        print(f"\n" + "="*70)
        print("✅ Pipeline completed successfully!")
        print("="*70)
        print(f"\nOutput files:")
        for fmt, filepath in outputs.items():
            print(f"  • {fmt}: {os.path.abspath(filepath)}")

        print(f"\n📖 Open the HTML visualization in your browser:")
        print(f"  open {os.path.abspath(outputs['html'])}")

    except Exception as e:
        print(f"\n❌ Pipeline failed with error:")
        print(f"  {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
