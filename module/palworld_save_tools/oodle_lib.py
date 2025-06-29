import ctypes
import os
import sys
import struct

from enum import IntEnum
from typing import Tuple, Optional

# Default compressor dan level
OODLE_COMPRESSOR = 8  # Kraken
OODLE_LEVEL = 6       # Optimal2

class CtypesEnum(IntEnum):
    """A ctypes-compatible IntEnum superclass."""
    @classmethod
    def from_param(cls, obj):
        return int(obj)

class CompressionLevel(CtypesEnum):
    Null = 0
    SuperFast = 1
    VeryFast = 2
    Fast = 3
    Normal = 4

    Optimal1 = 5
    Optimal2 = 6
    Optimal3 = 7
    Optimal4 = 8
    Optimal5 = 9

    HyperFast1 = -1
    HyperFast2 = -2
    HyperFast3 = -3
    HyperFast4 = -4

    HyperFast = HyperFast1
    Optimal = Optimal2
    Max = Optimal5
    Min = HyperFast4

    Force32 = 0x40000000
    Invalid = Force32


class Compressor(CtypesEnum):
    Invalid = -1
    Null = 3

    Kraken = 8
    Leviathan = 13
    Mermaid = 9
    Selkie = 11
    Hydra = 12

    BitKnit = 10
    LZB16 = 4
    LZNA = 7
    LZH = 0
    LZHLW = 1
    LZNIB = 2
    LZBLW = 5
    LZA = 6

    Count = 14
    Force32 = 0x40000000

class CompressOptions(ctypes.Structure):
    _fields_ = [
        ("unused_was_verbosity", ctypes.c_uint32),
        ("minMatchLen", ctypes.c_int32),
        ("seekChunkReset", ctypes.c_int32),  # OO_BOOL is a 32-bit integer
        ("seekChunkLen", ctypes.c_int32),
        ("profile", ctypes.c_int32),
        ("dictionarySize", ctypes.c_int32),
        ("spaceSpeedTradeoffBytes", ctypes.c_int32),
        ("unused_was_maxHuffmansPerChunk", ctypes.c_int32),
        ("sendQuantumCRCs", ctypes.c_int32),  # OO_BOOL is a 32-bit integer
        ("maxLocalDictionarySize", ctypes.c_int32),
        ("makeLongRangeMatcher", ctypes.c_int32),  # OO_BOOL is a 32-bit integer
        ("matchTableSizeLog2", ctypes.c_int32),
        ("jobify", ctypes.c_int32),
        ("jobifyUserPtr", ctypes.c_void_p),
        ("farMatchMinLen", ctypes.c_int32),
        ("farMatchOffsetLog2", ctypes.c_int32),
        ("reserved", ctypes.c_uint32 * 4),
    ]
    
class OodleLib:
    def __init__(self):
        self.oodle_lib = None
        self._load_oodle_library()

    def _load_oodle_library(self):
        if sys.platform.startswith("linux"):
            lib_name = "liboo2corelinux64.so.9"
            lib_subdir = "Linux"
        elif sys.platform == "darwin":
            lib_name = "liboo2corelinux64.so.9"
            lib_subdir = "Linux"
        elif sys.platform.startswith("win"):
            lib_name = "oo2core_9_win64.dll"
            lib_subdir = "Windows"
        else:
            raise RuntimeError(f"Unsupported platform: {sys.platform}")

        # Find library file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        lib_path = os.path.join(
            script_dir, "libs", "oodle", "libs", lib_subdir, lib_name
        )
        lib_path = os.path.abspath(lib_path)

        if not os.path.exists(lib_path):
            raise FileNotFoundError(f"Oodle library not found: {lib_path}")

        try:
            self.oodle_lib = ctypes.CDLL(lib_path)
            self._setup_oodle_functions()
            print(f"Successfully loaded Oodle library: {lib_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to load Oodle library: {e}")

    def _setup_oodle_functions(self):
        """Setup Oodle function signatures"""
        # OodleLZ_Decompress function signature
        # SINTa OodleLZ_Decompress(const void* compBuf, SINTa compBufSize, void* rawBuf, SINTa rawLen, ...)
        self.oodle_lib.OodleLZ_Decompress.argtypes = [
            ctypes.c_void_p,  # compressed buffer
            ctypes.c_long,  # compressed size (SINTa)
            ctypes.c_void_p,  # raw buffer
            ctypes.c_long,  # raw length (SINTa)
            ctypes.c_int,  # fuzz_safe
            ctypes.c_int,  # check_crc
            ctypes.c_int,  # verbosity
            ctypes.c_void_p,  # decode buffer base
            ctypes.c_long,  # decode buffer size
            ctypes.c_void_p,  # fp_callback
            ctypes.c_void_p,  # callback userdata
            ctypes.c_void_p,  # scratch buffer
            ctypes.c_long,  # scratch size
            ctypes.c_int,  # thread phase
        ]
        self.oodle_lib.OodleLZ_Decompress.restype = ctypes.c_long  # SINTa

        self.oodle_lib.OodleLZ_Compress.argtypes = (
            Compressor,  # compressor
            ctypes.POINTER(ctypes.c_char),  # rawBuf
            ctypes.c_long,  # rawLen
            ctypes.POINTER(ctypes.c_char),  # compBuf
            CompressionLevel,  # level
            ctypes.POINTER(CompressOptions),  # pOptions
            ctypes.c_void_p,  # dictionaryBase
            ctypes.c_void_p,  # lrm
            ctypes.c_void_p,  # scratchMem
            ctypes.c_long,  # scratchSize
        )
        self.oodle_lib.OodleLZ_Compress.restype = ctypes.c_long
        
        self.oodle_lib.OodleLZ_GetCompressedBufferSizeNeeded.argtypes = (
            ctypes.c_uint,  # rawSize
        )
        self.oodle_lib.OodleLZ_GetCompressedBufferSizeNeeded.restype = ctypes.c_uint
        
        self.oodle_lib.OodleLZ_CompressOptions_GetDefault.argtypes = (
            Compressor,  # compressor
            CompressionLevel,  # lzLevel
        )
        self.oodle_lib.OodleLZ_CompressOptions_GetDefault.restype = ctypes.POINTER(CompressOptions)

    def check_sav_format(self, sav_data: bytes) -> int:
        """
        Check SAV file format
        Returns: 1=PLM(Oodle), 0=PLZ(Zlib), -1=Unknown
        """
        if len(sav_data) < 24:
            return -1

        # Determine header offset
        header_offset = 12 if sav_data.startswith(b"CNK") else 0

        if len(sav_data) < header_offset + 11:
            return -1

        # Check magic bytes
        magic = sav_data[header_offset + 8 : header_offset + 11]

        if magic == b"PlM":
            return 1  # PLM format (Oodle)
        elif magic == b"PlZ":
            return 0  # PLZ format (Zlib)
        else:
            return -1  # Unknown format

    def _parse_sav_header(self, sav_data: bytes) -> Tuple[int, int, bytes, int, int]:
        """
        Parse SAV file header
        Returns: (uncompressed length, compressed length, magic bytes, save type, data offset)
        """
        if len(sav_data) < 24:
            raise ValueError("File too small to parse header")

        # Determine header offset and data offset
        if sav_data.startswith(b"CNK"):
            header_offset = 12
            data_offset = 24
        else:
            header_offset = 0
            data_offset = 12

        # Parse header fields
        uncompressed_len = struct.unpack(
            "<I", sav_data[header_offset : header_offset + 4]
        )[0]
        compressed_len = struct.unpack(
            "<I", sav_data[header_offset + 4 : header_offset + 8]
        )[0]
        magic = sav_data[header_offset + 8 : header_offset + 11]
        save_type = sav_data[header_offset + 11]

        return uncompressed_len, compressed_len, magic, save_type, data_offset

    def decompress_sav_to_gvas(self, sav_data: bytes) -> Tuple[bytes, int]:
        """
        Decompress SAV file to GVAS data

        Args:
            sav_data: SAV file bytes

        Returns:
            Tuple[bytes, int]: (GVAS data, save type)

        Raises:
            ValueError: Invalid input data
            RuntimeError: Decompression failed
        """
        if not sav_data:
            raise ValueError("SAV data cannot be empty")

        # Check format
        format_result = self.check_sav_format(sav_data)
        if format_result == 0:
            raise ValueError(
                "Detected PLZ format (Zlib), this tool only supports PLM format (Oodle)"
            )
        elif format_result == -1:
            raise ValueError("Unknown SAV file format")

        print("Detected PLM format (Oodle), starting decompression...")

        # Parse header
        uncompressed_len, compressed_len, magic, save_type, data_offset = (
            self._parse_sav_header(sav_data)
        )

        print(f"File information:")
        print(f"  Magic bytes: {magic.decode('ascii', errors='ignore')}")
        print(f"  Save type: 0x{save_type:02X}")
        print(f"  Compressed size: {compressed_len:,} bytes")
        print(f"  Uncompressed size: {uncompressed_len:,} bytes")
        print(f"  Data offset: {data_offset} bytes")

        # Check if the data is complete
        if len(sav_data) < data_offset + compressed_len:
            raise ValueError(
                f"File data is incomplete, expected {data_offset + compressed_len} bytes, actual {len(sav_data)} bytes"
            )

        compressed_data = sav_data[data_offset : data_offset + compressed_len]
        gvas_buffer = ctypes.create_string_buffer(uncompressed_len)

        print("Calling Oodle decompression...")
        result = self.oodle_lib.OodleLZ_Decompress(
            compressed_data,  # compressed buffer
            compressed_len,  # compressed size
            gvas_buffer,  # output buffer
            uncompressed_len,  # expected output size
            1,  # fuzz_safe = Yes
            0,  # check_crc = No
            0,  # verbosity = None
            None,  # decode buffer base
            0,  # decode buffer size
            None,  # callback
            None,  # callback userdata
            None,  # scratch buffer
            0,  # scratch size
            3,  # thread phase = Unthreaded
        )

        if result < 0:
            raise RuntimeError(f"Oodle decompression failed, error code: {result}")

        if result != uncompressed_len:
            raise RuntimeError(
                f"Decompression size mismatch, expected: {uncompressed_len}, actual: {result}"
            )

        gvas_data = gvas_buffer.raw[:result]

        print(f"Decompression successful! GVAS size: {len(gvas_data):,} bytes")

        return gvas_data, save_type

    def decompress_file(self, sav_file_path: str, gvas_file_path: str) -> int:
        """
        Decompress SAV file to GVAS file

        Args:
            sav_file_path: Input SAV file path
            gvas_file_path: Output GVAS file path

        Returns:
            int: Save type
        """
        print(f"Reading SAV file: {sav_file_path}")

        with open(sav_file_path, "rb") as f:
            sav_data = f.read()

        gvas_data, save_type = self.decompress_sav_to_gvas(sav_data)

        print(f"Writing GVAS file: {gvas_file_path}")
        with open(gvas_file_path, "wb") as f:
            f.write(gvas_data)

        return save_type
    
    def compress_gvas_to_sav(self, gvas_data: bytes, save_type: int) -> bytes:
        """        Compress GVAS data to SAV format
        Args:
            gvas_data: GVAS data bytes
            save_type: Save type byte (0x32 for Zlib, 0x31 for oodle)
        Returns:
            bytes: Compressed SAV data
        Raises:
            ValueError: If input data is empty
            RuntimeError: If compression fails"""
        src_len = len(gvas_data)
        if src_len == 0:
            raise ValueError("Data input tidak boleh kosong.")

  
        src_array = (ctypes.c_char * src_len).from_buffer_copy(gvas_data)

        max_comp_len = self.oodle_lib.OodleLZ_GetCompressedBufferSizeNeeded(src_len)
        comp_array = ctypes.create_string_buffer(max_comp_len)

        # CompressOptions default (optional)
        compress_options = self.oodle_lib.OodleLZ_CompressOptions_GetDefault(
            OODLE_COMPRESSOR,  # compressor
            OODLE_LEVEL,       # lzLevel
        )
        compress_options.contents.seekChunkReset = True
        compress_options.contents.seekChunkLen = 0x40000

        compressed_len = self.oodle_lib.OodleLZ_Compress(
            OODLE_COMPRESSOR,
            src_array,
            src_len,
            comp_array,
            OODLE_LEVEL,
            compress_options,
            ctypes.c_void_p(),
            ctypes.c_void_p(),
            ctypes.c_void_p(),
            0,  # scratchSize
        )

        if compressed_len <= 0:
            raise RuntimeError(f"Oodle compression failed with code: {compressed_len}")

        # create header SAV
        result = bytearray()
        result.extend(src_len.to_bytes(4, "little"))
        result.extend(compressed_len.to_bytes(4, "little"))
        result.extend(b"PlM")
        result.append(save_type)
        result.extend(comp_array[:compressed_len])

        return bytes(result)

def main():
    """Main function - command line interface"""
    if len(sys.argv) != 3:
        print("Usage: python oodle_decompressor.py <input.sav> <output.gvas>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not os.path.exists(input_file):
        print(f"Error: input file does not exist: {input_file}")
        sys.exit(1)

    try:
        decompressor = OodleLib()
        save_type = decompressor.decompress_file(input_file, output_file)
        print(f"Decompression completed! Save type: 0x{save_type:02X}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
