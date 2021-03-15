SAMPLE_BMETA = {
    "build": {
        "duration": 315.772096157074,
        "status": "PASS"
    },
    "environment": {
        "arch": "arm64",
        "compiler": "gcc",
        "compiler_version": "8",
        "compiler_version_full": "\
aarch64-linux-gnu-gcc (Debian 8.3.0-2) 8.3.0",
        "cross_compile": "aarch64-linux-gnu-",
        "cross_compile_compat": "arm-linux-gnueabihf-",
        "make_opts": {
            "KBUILD_BUILD_USER": "KernelCI"
        },
        "name": "gcc-8",
        "platform": {
            "uname": [
                "Linux",
                "3ddfd7c7bfde",
                "4.19.0-12-amd64",
                "#1 SMP Debian 4.19.152-1 (2020-10-18)",
                "x86_64",
                ""
            ]
        },
        "use_ccache": True
    },
    "kernel": {
        "defconfig": "defconfig",
        "defconfig_expanded": "defconfig+kernel/configs/kselftest.config",
        "defconfig_extras": [
            "kselftest"
        ],
        "defconfig_full": "defconfig+kselftest",
        "fragments": [
            "kernelci.config"
        ],
        "image": "Image",
        "publish_path": "\
next/master/next-20210304/arm64/defconfig+kselftest/gcc-8",
        "system_map": "System.map",
        "text_offset": "0x10000000",
        "vmlinux_bss_size": 11538800,
        "vmlinux_data_size": 4667528,
        "vmlinux_file_size": 573708760,
        "vmlinux_text_size": 19608792
    },
    "revision": {
        "branch": "master",
        "commit": "f5427c2460ebc11b1a66c1742d41077ae5b99796",
        "describe": "next-20210304",
        "describe_verbose": "v5.12-rc1-1897-gf5427c2460eb",
        "tree": "next",
        "url": "\
https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git"
    }
}

SAMPLE_STEPS = [
    {
        "cpus": {
            "Intel Core Processor (Skylake, IBRS)": 3
        },
        "duration": 14.66972279548645,
        "name": "revision",
        "start_time": "2021-03-12T15:04:52.856716",
        "status": "PASS"
    },
    {
        "cpus": {
            "Intel Core Processor (Skylake, IBRS)": 3
        },
        "duration": 23.788511037826538,
        "log_file": "config.log",
        "name": "config",
        "start_time": "2021-03-12T15:05:07.803411",
        "status": "PASS",
        "threads": "4"
    },
    {
        "cpus": {
            "Intel Core Processor (Skylake, IBRS)": 3
        },
        "duration": 0.0017621517181396484,
        "log_file": "config.log",
        "name": "config install",
        "start_time": "2021-03-12T15:05:31.592204",
        "status": "PASS"
    },
    {
        "cpus": {
            "Intel Core Processor (Skylake, IBRS)": 3
        },
        "duration": 258.61317110061646,
        "log_file": "kernel.log",
        "name": "kernel",
        "start_time": "2021-03-12T15:05:31.851197",
        "status": "PASS",
        "threads": "4"
    },
]

SAMPLE_ARTIFACTS = {
    "config": [
        {
            "key": "config",
            "path": "config/kernel.config",
            "type": "file"
        },
        {
            "key": "fragment",
            "path": "config/kernelci.config",
            "type": "file"
        },
        {
            "key": "log",
            "path": "logs/config.log",
            "type": "file"
        }
    ],
    "dtbs": [
        {
            "contents": [
                "actions/s700-cubieboard7.dtb",
                "actions/s900-bubblegum-96.dtb",
                # ...
                "xilinx/zynqmp-zcu106-revA.dtb",
                "xilinx/zynqmp-zcu111-revA.dtb"
            ],
            "path": "dtbs",
            "type": "directory"
        },
        {
            "key": "log",
            "path": "logs/dtbs.log",
            "type": "file"
        }
    ],
    "kernel": [
        {
            "key": "system_map",
            "path": "kernel/System.map",
            "type": "file"
        },
        {
            "key": "image",
            "path": "kernel/Image",
            "type": "file"
        },
        {
            "key": "log",
            "path": "logs/kernel.log",
            "type": "file"
        }
    ],
    "modules": [
        {
            "contents": [
                "act_bpf.ko",
                "act_connmark.ko",
                # ...
                "zaurus.ko",
                "zstd_compress.ko"
            ],
            "path": "modules.tar.xz",
            "type": "tarball"
        },
        {
            "key": "log",
            "path": "logs/modules.log",
            "type": "file"
        }
    ]
}

SAMPLE_META = {
    "bmeta": SAMPLE_BMETA,
    "steps": SAMPLE_STEPS,
    "artifacts": SAMPLE_ARTIFACTS,
}
