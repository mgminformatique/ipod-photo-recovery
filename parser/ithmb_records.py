from pathlib import Path
import struct


GUID = "00262001-0002-0010-FBB3-AB02A8125552"
GUID_UTF16LE = GUID.encode("utf-16le")


class ITHMBRecord:
    def __init__(self, file_path, record_start, data):
        self.file_path = Path(file_path)
        self.record_start = record_start
        self.data = data

    def u32(self, offset):
        return struct.unpack_from("<I", self.data, offset)[0]

    def fields(self):
        return {
            "record_start": self.record_start,
            "field_00": self.u32(0),
            "field_04": self.u32(4),
            "field_88": self.u32(88),
            "field_92": self.u32(92),
            "field_96": self.u32(96),
            "field_100": self.u32(100),
            "field_104": self.u32(104),
            "field_108": self.u32(108),
        }


class ITHMBRecordParser:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.path.read_bytes()

    def find_records(self):
        records = []
        pos = 0

        while True:
            idx = self.data.find(GUID_UTF16LE, pos)

            if idx == -1:
                break

            record_start = idx - 16

            if record_start >= 0:
                record_data = self.data[record_start:record_start + 112]

                if len(record_data) == 112:
                    records.append(
                        ITHMBRecord(
                            file_path=self.path,
                            record_start=record_start,
                            data=record_data,
                        )
                    )

            pos = idx + 2

        return records
