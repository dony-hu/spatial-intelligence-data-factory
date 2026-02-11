"""
Factory Demo Scenarios - Pre-defined product requirements and test data
"""

from tools.factory_framework import ProductRequirement, ProductType, generate_id
from datetime import datetime


def get_address_cleaning_scenario() -> ProductRequirement:
    """Scenario 1: Address data cleaning and standardization"""
    return ProductRequirement(
        requirement_id=generate_id('req'),
        product_name='Shanghai Address Cleaning',
        product_type=ProductType.ADDRESS_CLEANING,
        input_format='raw_addresses',
        output_format='standardized_addresses',
        input_data=[
            {'raw': '上海市黄浦区中山东一路1号', 'source': 'customer_A'},
            {'raw': '上海黄浦中山东路10号', 'source': 'customer_B'},
            {'raw': '黄浦区南京东路100', 'source': 'customer_A'},
            {'raw': '上海浦东新区陆家嘴环路1000号', 'source': 'customer_C'},
            {'raw': '浦东陆家嘴1000', 'source': 'customer_B'},
            {'raw': '上海市徐汇区淮海中路1000号', 'source': 'customer_A'},
            {'raw': '徐汇淮海路999', 'source': 'customer_C'},
            {'raw': '上海静安区南京西路1号', 'source': 'customer_B'},
            {'raw': '静安南京西1', 'source': 'customer_A'},
            {'raw': '上海虹口区四川北路1号', 'source': 'customer_C'},
        ],
        sla_metrics={
            'max_duration': 60,  # 1 hour
            'quality_threshold': 0.95,
            'accuracy_requirement': 'high'
        },
        priority=1
    )


def get_entity_fusion_scenario() -> ProductRequirement:
    """Scenario 2: Multi-source entity fusion"""
    return ProductRequirement(
        requirement_id=generate_id('req'),
        product_name='Multi-source Entity Fusion',
        product_type=ProductType.ENTITY_FUSION,
        input_format='multi_source_entities',
        output_format='fused_entities',
        input_data=[
            {
                'source1': 'Starbucks Shanghai Huangpu',
                'source2': '星巴克上海黄浦店',
                'source3': 'Coffee shop at Zhongshan Rd E'
            },
            {
                'source1': 'Jing An Temple',
                'source2': '静安寺',
                'source3': 'Buddhist temple in Jing An'
            },
            {
                'source1': 'Lujiazui Financial District',
                'source2': '陆家嘴金融区',
                'source3': 'Finance district in Pudong'
            },
            {
                'source1': 'Nanjing Road',
                'source2': '南京路',
                'source3': 'Main shopping street'
            },
            {
                'source1': 'The Bund',
                'source2': '外滩',
                'source3': 'Riverside promenade'
            },
        ],
        sla_metrics={
            'max_duration': 90,
            'quality_threshold': 0.92,
            'deduplication_accuracy': 0.98
        },
        priority=2
    )


def get_relationship_extraction_scenario() -> ProductRequirement:
    """Scenario 3: Entity relationship extraction"""
    return ProductRequirement(
        requirement_id=generate_id('req'),
        product_name='Address Relationship Extraction',
        product_type=ProductType.RELATIONSHIP_EXTRACTION,
        input_format='standardized_addresses',
        output_format='entity_relationships',
        input_data=[
            {'address': '上海市黄浦区中山东一路1号', 'category': 'commercial'},
            {'address': '上海市黄浦区中山东一路10号', 'category': 'commercial'},
            {'address': '上海市黄浦区南京东路100号', 'category': 'residential'},
            {'address': '上海市浦东新区陆家嘴环路1000号', 'category': 'commercial'},
            {'address': '上海市浦东新区陆家嘴环路1100号', 'category': 'residential'},
            {'address': '上海市徐汇区淮海中路1000号', 'category': 'commercial'},
            {'address': '上海市徐汇区淮海中路1200号', 'category': 'residential'},
            {'address': '上海市静安区南京西路1号', 'category': 'commercial'},
            {'address': '上海市静安区南京西路200号', 'category': 'residential'},
            {'address': '上海市虹口区四川北路1号', 'category': 'commercial'},
        ],
        sla_metrics={
            'max_duration': 120,
            'quality_threshold': 0.93,
            'relationship_accuracy': 0.95
        },
        priority=3
    )


def get_small_dataset_scenario() -> ProductRequirement:
    """Quick test scenario with small dataset"""
    return ProductRequirement(
        requirement_id=generate_id('req'),
        product_name='Quick Test Dataset',
        product_type=ProductType.ADDRESS_CLEANING,
        input_format='raw_addresses',
        output_format='standardized_addresses',
        input_data=[
            {'raw': '上海黄浦中山东路1号', 'source': 'test'},
            {'raw': '上海浦东陆家嘴1000号', 'source': 'test'},
            {'raw': '上海徐汇淮海路1000', 'source': 'test'},
        ],
        sla_metrics={
            'max_duration': 30,
            'quality_threshold': 0.9
        },
        priority=5
    )


def get_custom_scenario(
    product_name: str,
    input_data: list,
    product_type: ProductType = ProductType.CUSTOM,
    quality_threshold: float = 0.9,
    max_duration: int = 120,
    priority: int = 5
) -> ProductRequirement:
    """Create a custom product requirement"""
    return ProductRequirement(
        requirement_id=generate_id('req'),
        product_name=product_name,
        product_type=product_type,
        input_format='custom_input',
        output_format='custom_output',
        input_data=input_data,
        sla_metrics={
            'max_duration': max_duration,
            'quality_threshold': quality_threshold
        },
        priority=priority
    )


def get_all_scenarios():
    """Get all pre-defined scenarios"""
    return {
        'address_cleaning': get_address_cleaning_scenario,
        'entity_fusion': get_entity_fusion_scenario,
        'relationship_extraction': get_relationship_extraction_scenario,
        'quick_test': get_small_dataset_scenario,
    }
