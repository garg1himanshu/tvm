# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import argparse
import os
import shutil
from os import path

import pytest

import tvm

from tvm.driver import tvmc


def test_save_dumps(tmpdir_factory):
    tmpdir = tmpdir_factory.mktemp("data")
    dump_formats = {"relay": "fake relay", "ll": "fake llvm", "asm": "fake asm"}
    tvmc.compiler.save_dumps("fake_module", dump_formats, dump_root=tmpdir)

    assert path.exists("{}/{}".format(tmpdir, "fake_module.ll"))
    assert path.exists("{}/{}".format(tmpdir, "fake_module.asm"))
    assert path.exists("{}/{}".format(tmpdir, "fake_module.relay"))


# End to end tests for compilation


def verify_compile_tflite_module(model, shape_dict=None):
    pytest.importorskip("tflite")

    graph, lib, params, dumps = tvmc.compiler.compile_model(
        model, target="llvm", dump_code="ll", alter_layout="NCHW", shape_dict=shape_dict
    )

    # check for output types
    assert type(graph) is str
    assert type(lib) is tvm.runtime.module.Module
    assert type(params) is dict
    assert type(dumps) is dict


def test_compile_tflite_module(tflite_mobilenet_v1_1_quant):
    # some CI environments wont offer tflite, so skip in case it is not present
    pytest.importorskip("tflite")
    # Check default compilation.
    verify_compile_tflite_module(tflite_mobilenet_v1_1_quant)
    # Check with manual shape override
    shape_string = "input:[1,224,224,3]"
    shape_dict = tvmc.common.parse_shape_string(shape_string)
    verify_compile_tflite_module(tflite_mobilenet_v1_1_quant, shape_dict)


# This test will be skipped if the AArch64 cross-compilation toolchain is not installed.
@pytest.mark.skipif(
    not shutil.which("aarch64-linux-gnu-gcc"), reason="cross-compilation toolchain not installed"
)
def test_cross_compile_aarch64_tflite_module(tflite_mobilenet_v1_1_quant):
    pytest.importorskip("tflite")

    graph, lib, params, dumps = tvmc.compiler.compile_model(
        tflite_mobilenet_v1_1_quant,
        target="llvm -device=arm_cpu -mtriple=aarch64-linux-gnu -mattr=+neon",
        dump_code="asm",
    )

    # check for output types
    assert type(graph) is str
    assert type(lib) is tvm.runtime.module.Module
    assert type(params) is dict
    assert type(dumps) is dict


def test_compile_keras__save_module(keras_resnet50, tmpdir_factory):
    # some CI environments wont offer tensorflow/Keras, so skip in case it is not present
    pytest.importorskip("tensorflow")

    graph, lib, params, dumps = tvmc.compiler.compile_model(
        keras_resnet50, target="llvm", dump_code="ll"
    )

    expected_temp_dir = tmpdir_factory.mktemp("saved_output")
    expected_file_name = "saved.tar"
    module_file = os.path.join(expected_temp_dir, expected_file_name)
    tvmc.compiler.save_module(module_file, graph, lib, params)

    assert os.path.exists(module_file), "output file {0} should exist".format(module_file)


# This test will be skipped if the AArch64 cross-compilation toolchain is not installed.
@pytest.mark.skipif(
    not shutil.which("aarch64-linux-gnu-gcc"), reason="cross-compilation toolchain not installed"
)
def test_cross_compile_aarch64_keras_module(keras_resnet50):
    # some CI environments wont offer tensorflow/Keras, so skip in case it is not present
    pytest.importorskip("tensorflow")

    graph, lib, params, dumps = tvmc.compiler.compile_model(
        keras_resnet50,
        target="llvm -device=arm_cpu -mtriple=aarch64-linux-gnu -mattr=+neon",
        dump_code="asm",
    )

    # check for output types
    assert type(graph) is str
    assert type(lib) is tvm.runtime.module.Module
    assert type(params) is dict
    assert type(dumps) is dict
    assert "asm" in dumps.keys()


def verify_compile_onnx_module(model, shape_dict=None):
    # some CI environments wont offer onnx, so skip in case it is not present
    pytest.importorskip("onnx")

    graph, lib, params, dumps = tvmc.compiler.compile_model(
        model, target="llvm", dump_code="ll", shape_dict=shape_dict
    )

    # check for output types
    assert type(graph) is str
    assert type(lib) is tvm.runtime.module.Module
    assert type(params) is dict
    assert type(dumps) is dict
    assert "ll" in dumps.keys()


def test_compile_onnx_module(onnx_resnet50):
    # Test default compilation
    verify_compile_onnx_module(onnx_resnet50)
    # Test with manual shape dict
    shape_string = "data:[1,3,200,200]"
    shape_dict = tvmc.common.parse_shape_string(shape_string)
    verify_compile_onnx_module(onnx_resnet50, shape_dict)


# This test will be skipped if the AArch64 cross-compilation toolchain is not installed.
@pytest.mark.skipif(
    not shutil.which("aarch64-linux-gnu-gcc"), reason="cross-compilation toolchain not installed"
)
def test_cross_compile_aarch64_onnx_module(onnx_resnet50):
    # some CI environments wont offer onnx, so skip in case it is not present
    pytest.importorskip("onnx")

    graph, lib, params, dumps = tvmc.compiler.compile_model(
        onnx_resnet50,
        target="llvm -device=arm_cpu -mtriple=aarch64-linux-gnu -mattr=+neon",
        dump_code="asm",
    )

    # check for output types
    assert type(graph) is str
    assert type(lib) is tvm.runtime.module.Module
    assert type(params) is dict
    assert type(dumps) is dict
    assert "asm" in dumps.keys()


@tvm.testing.requires_opencl
def test_compile_opencl(tflite_mobilenet_v1_0_25_128):
    pytest.importorskip("tflite")

    graph, lib, params, dumps = tvmc.compiler.compile_model(
        tflite_mobilenet_v1_0_25_128,
        target="opencl",
        target_host="llvm",
        alter_layout="NCHW",
    )

    # check for output types
    assert type(graph) is str
    assert type(lib) is tvm.runtime.module.Module
    assert type(params) is dict
    assert type(dumps) is dict
