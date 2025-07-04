from typing import Any, Sequence

from palworld_save_tools.archive import *


def decode(
    reader: FArchiveReader, type_name: str, size: int, path: str
) -> dict[str, Any]:
    if type_name != "ArrayProperty":
        raise Exception(f"Expected ArrayProperty, got {type_name}")
    value = reader.property(type_name, size, path, nested_caller_path=path)
    data_bytes = value["value"]["values"]
    value["value"] = decode_bytes(reader, data_bytes)
    return value


def decode_bytes(
    parent_reader: FArchiveReader, c_bytes: Sequence[int]
) -> Optional[dict[str, Any]]:
    if len(c_bytes) == 0:
        return None

    try:
        reader = parent_reader.internal_copy(bytes(c_bytes), debug=False)
        data: dict[str, Any] = {}
        data["permission"] = {
            "type_a": reader.tarray(lambda r: r.byte()),
            "type_b": reader.tarray(lambda r: r.byte()),
            "item_static_ids": reader.tarray(lambda r: r.fstring()),
        }
        data["corruption_progress_value"] = reader.float()
        if not reader.eof():
            data["trailing_unparsed_data"] = [b for b in reader.read_to_end()]
        return data
    except Exception as e:
        print(f"Error in decode_bytes: {e}")
        return {"raw_bytes": c_bytes}


def encode(
    writer: FArchiveWriter, property_type: str, properties: dict[str, Any]
) -> int:
    if property_type != "ArrayProperty":
        raise Exception(f"Expected ArrayProperty, got {property_type}")
    del properties["custom_type"]
    encoded_bytes = encode_bytes(properties["value"])
    properties["value"] = {"values": [b for b in encoded_bytes]}
    return writer.property_inner(property_type, properties)


def encode_bytes(p: dict[str, Any]) -> bytes:
    if p is None:
        return bytes()
    if "raw_bytes" in p:
        # This is raw data, just return it
        if isinstance(p["raw_bytes"], list):
            return bytes(p["raw_bytes"])
        return bytes()
    writer = FArchiveWriter()
    writer.tarray(lambda w, d: w.byte(d), p["permission"]["type_a"])
    writer.tarray(lambda w, d: w.byte(d), p["permission"]["type_b"])
    writer.tarray(
        lambda w, d: (w.fstring(d), None)[1], p["permission"]["item_static_ids"]
    )
    writer.float(p["corruption_progress_value"])
    if "trailing_unparsed_data" in p:
        writer.write(bytes(p["trailing_unparsed_data"]))
    encoded_bytes = writer.bytes()
    return encoded_bytes
