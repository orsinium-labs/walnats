from google.protobuf import descriptor_pool
from google.protobuf.internal import builder  # type: ignore[attr-defined]


DESCRIPTOR = descriptor_pool.Default().AddSerializedFile(
    b'\n\x0eprotobuf.proto\x12\x05tests\"\x19\n\x08Protobuf\x12\r\n\x05value\x18\x01 \x02(\t',  # noqa: E501
)

builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'protobuf_pb2', globals())
