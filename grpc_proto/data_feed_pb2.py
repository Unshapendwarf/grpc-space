# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: data_feed.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0f\x64\x61ta_feed.proto\x12\x08\x64\x61tafeed\")\n\x06\x43onfig\x12\r\n\x05index\x18\x01 \x01(\x05\x12\x10\n\x08\x66ilename\x18\x02 \x01(\t\"r\n\x06Sample\x12 \n\x06\x66rames\x18\x01 \x01(\x0b\x32\x10.datafeed.Frames\x12$\n\x08st_times\x18\x02 \x01(\x0b\x32\x12.datafeed.ST_times\x12 \n\x06tdiffs\x18\x03 \x01(\x0b\x32\x10.datafeed.Tdiffs\"(\n\x06\x46rames\x12\x0e\n\x06\x66rame1\x18\x01 \x01(\x0c\x12\x0e\n\x06\x66rame2\x18\x02 \x01(\x0c\".\n\x08ST_times\x12\x10\n\x08st_time1\x18\x01 \x03(\x02\x12\x10\n\x08st_time2\x18\x02 \x03(\x02\"(\n\x06Tdiffs\x12\x0e\n\x06tdiff1\x18\x01 \x03(\x02\x12\x0e\n\x06tdiff2\x18\x02 \x03(\x02\x32>\n\x08\x44\x61taFeed\x12\x32\n\nget_sample\x12\x10.datafeed.Config\x1a\x10.datafeed.Sample\"\x00\x62\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'data_feed_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _CONFIG._serialized_start=29
  _CONFIG._serialized_end=70
  _SAMPLE._serialized_start=72
  _SAMPLE._serialized_end=186
  _FRAMES._serialized_start=188
  _FRAMES._serialized_end=228
  _ST_TIMES._serialized_start=230
  _ST_TIMES._serialized_end=276
  _TDIFFS._serialized_start=278
  _TDIFFS._serialized_end=318
  _DATAFEED._serialized_start=320
  _DATAFEED._serialized_end=382
# @@protoc_insertion_point(module_scope)
