# Imports
import MalmoPython as Malmo


def create_inventory(weapon_tier: int = 0, armor_tier: int = 0):
    """
    Generates an inventory XML segment based on requirements

    Args:
        weapon_tier (int): 0 - wooden; 1 - gold; 2 - stone; 3 - iron; 4 - diamond
        armor_tier (int): 0 - none; 1 - leather; 2 - gold; 3 - chain; 4 - iron; 5 - diamond

    Returns:
        String: string containing inventory portion of the mission XML
    """
    assert 0 <= weapon_tier <= 4, f"Expected weapon tier (0-4), got \"{weapon_tier}\""
    assert 0 <= armor_tier <= 5, f"Expected armor tier (0-5), got \"{armor_tier}\""

    weapon_tiers = ["wooden", "golden", "stone", "iron", "diamond"]
    armor_tiers = ["", "leather", "golden", "chainmail", "iron", "diamond"]

    # Set weapons
    xml = f"""<Inventory>
    <InventoryObject type="{weapon_tiers[weapon_tier]}_sword" slot="0"/>
    <InventoryObject type="{weapon_tiers[weapon_tier]}_axe" slot="1"/>
    <InventoryObject type="shield" slot="8"/>
    """

    # Set armor
    if armor_tier > 0:
        for i, armor_type in enumerate(["helmet", "chestplate", "leggings", "boots"]):
            xml += f"<InventoryObject type=\"{armor_tiers[armor_tier]}_{armor_type}\" slot=\"{39 - i}\"/>"

    xml += "</Inventory>"
    return xml
