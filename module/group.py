from typing import Sequence

from palworld_save_tools.archive import *


def decode(
    reader: FArchiveReader, type_name: str, size: int, path: str
) -> dict[str, Any]:
    if type_name != "MapProperty":
        raise Exception(f"Expected MapProperty, got {type_name}")
    value = reader.property(type_name, size, path, nested_caller_path=path)
    # Decode the raw bytes and replace the raw data
    group_map = value["value"]
    for group in group_map:
        group_type = group["value"]["GroupType"]["value"]["value"]
        group_bytes = group["value"]["RawData"]["value"]["values"]
        try:
            group["value"]["RawData"]["value"] = decode_bytes(
                reader, group_bytes, group_type
            )
        except Exception as e:
            print(f"Skipping reading 1 group: {e}")
    return value


def decode_bytes(
    parent_reader: FArchiveReader, group_bytes: Sequence[int], group_type: str
) -> dict[str, Any]:
    reader = parent_reader.internal_copy(bytes(group_bytes), debug=False)
    group_data = {
        "group_type": group_type,
        "group_id": reader.guid(),
        "group_name": reader.fstring(),
        "individual_character_handle_ids": reader.tarray(instance_id_reader),
    }
    if group_type in [
        "EPalGroupType::Guild",
        "EPalGroupType::IndependentGuild",
        "EPalGroupType::Organization",
    ]:
        org = {
            "org_type": reader.byte(),
            "base_ids": reader.tarray(uuid_reader),
        }
        group_data |= org
    if group_type in ["EPalGroupType::Guild", "EPalGroupType::IndependentGuild"]:
        guild: dict[str, Any] = {
            "base_camp_level": reader.i32(),
            "map_object_instance_ids_base_camp_points": reader.tarray(uuid_reader),
            "guild_name": reader.fstring(),
        }
        group_data |= guild
    if group_type == "EPalGroupType::IndependentGuild":
        indie = {
            "player_uid": reader.guid(),
            "guild_name_2": reader.fstring(),
            "player_info": {
                "last_online_real_time": reader.i64(),
                "player_name": reader.fstring(),
            },
        }
        group_data |= indie
    if group_type == "EPalGroupType::Guild":
        guild = {
            # these are unknown values that don't seem to have any meaning
            "u1": reader.i64(), # perhaps like history_admin_player_uid
            "u2": reader.i64(), # always 0, not sure what this is
            "admin_player_uid": reader.guid(),
            "players": [],
        }
        player_count = reader.i32()
        for _ in range(player_count):
            player = {
                "player_uid": reader.guid(),
                "player_info": {
                    "last_online_real_time": reader.i64(),
                    "player_name": reader.fstring(),
                },
            }
            guild["players"].append(player)
        group_data |= guild
    if not reader.eof():
        raise Exception("Warning: EOF not reached")
    return group_data


def encode(
    writer: FArchiveWriter, property_type: str, properties: dict[str, Any]
) -> int:
    if property_type != "MapProperty":
        raise Exception(f"Expected MapProperty, got {property_type}")
    del properties["custom_type"]
    group_map = properties["value"]
    for group in group_map:
        if "values" in group["value"]["RawData"]["value"]:
            continue
        p = group["value"]["RawData"]["value"]
        encoded_bytes = encode_bytes(p)
        group["value"]["RawData"]["value"] = {"values": [b for b in encoded_bytes]}
    return writer.property_inner(property_type, properties)


def encode_bytes(p: dict[str, Any]) -> bytes:
    writer = FArchiveWriter()
    writer.guid(p["group_id"])
    writer.fstring(p["group_name"])
    writer.tarray(instance_id_writer, p["individual_character_handle_ids"])
    if p["group_type"] in [
        "EPalGroupType::Guild",
        "EPalGroupType::IndependentGuild",
        "EPalGroupType::Organization",
    ]:
        writer.byte(p["org_type"])
        writer.tarray(uuid_writer, p["base_ids"])
    if p["group_type"] in ["EPalGroupType::Guild", "EPalGroupType::IndependentGuild"]:
        writer.i32(p["base_camp_level"])
        writer.tarray(uuid_writer, p["map_object_instance_ids_base_camp_points"])
        writer.fstring(p["guild_name"])
    if p["group_type"] == "EPalGroupType::IndependentGuild":
        writer.guid(p["player_uid"])
        writer.fstring(p["guild_name_2"])
        writer.i64(p["player_info"]["last_online_real_time"])
        writer.fstring(p["player_info"]["player_name"])
    if p["group_type"] == "EPalGroupType::Guild":
        writer.guid(p["admin_player_uid"])
        writer.i32(len(p["players"]))
        for i in range(len(p["players"])):
            writer.guid(p["players"][i]["player_uid"])
            writer.i64(p["players"][i]["player_info"]["last_online_real_time"])
            writer.fstring(p["players"][i]["player_info"]["player_name"])
    encoded_bytes = writer.bytes()
    return encoded_bytes
