import argparse
import os
import random
import shutil
import string
import subprocess
import tqdm
import matplotlib.pyplot as plt

_base_int_types = [
    "signed char",
    "unsigned char",
    "short int",
    "unsigned short int",
    "int",
    "unsigned int",
    "long int",
    "unsigned long int",
    "long long int",
    "unsigned long long int",
]
_base_bool_types = ["bool"]
_base_char_types = [
    "signed char",
    "unsigned char",
    "wchar_t",
    "char16_t",
]
_base_fp_types = [
    "float",
    "double",
    "long double",
]
_base_types = []
_base_types.extend(_base_int_types)
_base_types.extend(_base_bool_types)
_base_types.extend(_base_char_types)
_base_types.extend(_base_fp_types)

SEED = 0


def gen(args):
    try:
        shutil.rmtree("autogen")
        shutil.rmtree("plots")
    except:
        pass
    os.mkdir("autogen")
    os.mkdir("autogen/pcms")
    os.mkdir("plots")
    main_header = "template<typename T, typename ...Ts> class Pattern { T field; };\n"
    with open("autogen/main_header.hpp", "w+") as f:
        f.write(main_header)
    aux_headers = []
    main_specls_used = []
    print(args)
    for header_id in tqdm.tqdm(range(1, args.headers)):
        header_path = f"autogen/{header_id}.hpp"
        with open(f"{header_path}", "w+") as f:
            specl = '#include "main_header.hpp"\n\n'
            for specl_id in range(0, args.specls):
                struct_name = f"aux_header{header_id}{specl_id}"
                specl += f"struct {struct_name}" + "{};\n"
                specl += "template<> class " + f"Pattern<{struct_name}>" + "{};\n"
                main_specls_used.append(f"Pattern<{struct_name}>")
            f.write(specl)
        aux_headers.append(header_path)

    with open("autogen/module.modulemap", "w+") as f:
        module_map = """  module main_header {
    export *
    header "main_header.hpp"
  }
"""
        for header_id in range(1, args.headers):
            module_map += (
                f'  module "{header_id}" '
                + """{
    export *
    header \""""
                + str(header_id)
                + """.hpp\"
  }\n"""
            )
        f.write(module_map)

    # write main file
    with open("autogen/main.cpp", "w+") as f:
        main_file = '#include "main_header.hpp"\n'
        for header_id in range(1, args.headers):
            main_file += f'#include "{header_id}.hpp"\n'
        main_file += "\n"
        main_file += "int main(){\n"
        for specl_id in range(0, args.pspecls):
            main_file += (
                "\t"
                + main_specls_used[random.randint(0, len(main_specls_used) - 1)]
                + " "
                + "".join(random.choices(string.ascii_uppercase, k=12))
            )
            main_file += ";\n"
        main_file += "}\n"
        f.write(main_file)

    module_args_string = "-fmodules -fmodule-map-file=./autogen/module.modulemap"

    # compile main header
    res = subprocess.run(
        args.clang_path
        + " -x c++-header -Xclang -emit-module -o autogen/pcms/main_header.pcm -fmodules autogen/module.modulemap -fmodule-name=main_header -std=c++17 2>&1",
        capture_output=True,
        shell=True,
    )
    if "error" in res.stdout.decode():
        print("*****************Error************************")
        print(res.stdout.decode())
        exit(1)
    module_args_string += " -fmodule-file=main_header=./autogen/pcms/main_header.pcm "

    for header_id in range(1, args.headers):
        res = subprocess.run(
            args.clang_path
            + f" -x c++-header -Xclang -emit-module -o autogen/pcms/{header_id}.pcm -fmodules autogen/module.modulemap -fmodule-name={header_id} -fmodule-file={header_id}=./autogen/pcms/{header_id}.pcm -fmodule-file=main_header=./autogen/pcms/main_header.pcm -std=c++17 2>&1",
            capture_output=True,
            shell=True,
        )
        if "error" in res.stdout.decode():
            print("*****************Error************************")
            print(res.stdout.decode())
            exit(1)
        module_args_string += (
            f" -fmodule-file={header_id}=./autogen/pcms/{header_id}.pcm "
        )

    avg = 0
    memory_avg = 0
    for _ in tqdm.tqdm(range(0, args.compile_runs)):
        res = subprocess.run(
            "/usr/bin/time -v "
            + args.clang_path
            + f"  -std=c++17 ./autogen/main.cpp {module_args_string} -Xclang -print-stats -ftime-report 2>&1",
            capture_output=True,
            shell=True,
        )
        if "error" in res.stderr.decode():
            print(f"Error in clang: {res.stderr.decode()}")
            exit(1)
        true_res = res.stdout.decode().split("Clang front-end time report")[1]
        memory_current = (
            float(
                (
                    res.stdout.decode()
                    .split("Maximum resident set size (kbytes):")[1]
                    .split("\n")[0]
                ).strip()
            )
            / 1000
        )
        memory_avg += memory_current
        total_ex_time = "".join(true_res.split("seconds")[0])
        total_ex_time = "".join(total_ex_time.split("Time:")[1])
        total_ex_time = total_ex_time.strip()
        total_ex_time = float(total_ex_time)
        avg += total_ex_time
    avg = avg / args.compile_runs
    memory_avg = memory_avg / args.compile_runs
    print(f"Avg Total ex time: {avg} | Avg Max Resident Memory: {memory_avg}")
    return avg, memory_avg


if __name__ == "__main__":
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument(
        "--specls",
        help="Specify number of Template Specializations",
        action="store",
        default=5,
        type=int,
    )
    args_parser.add_argument(
        "--pspecls",
        help="Specify number of Partial Specializations to use in main.cpp",
        action="store",
        default=5,
        type=int,
    )
    args_parser.add_argument(
        "--headers",
        help="Number of Headers",
        action="store",
        default=1,
        type=int,
    )
    args_parser.add_argument(
        "--compile-runs",
        help="Number of runs to compile",
        action="store",
        default=6,
        type=int,
    )
    args_parser.add_argument(
        "--test-runs",
        help="Number of headers to plot",
        action="store",
        default=10,
        type=int,
    )
    args_parser.add_argument(
        "--test-run-steps",
        help="Number of steps",
        action="store",
        default=10,
        type=int,
    )
    args_parser.add_argument(
        "--test-run-start",
        help="Start point for tests",
        action="store",
        default=1,
        type=int,
    )
    args_parser.add_argument(
        "--clang-path",
        help="Boolean to compile each module",
        action="store",
        default="clang++",
    )
    args = args_parser.parse_args()

    random.seed(SEED)

    res = []
    headers = []
    args.clang_path = "clang++"
    on_disk_memory = []
    memory_resident_avg = []
    CONST = args.headers
    for i in range(args.test_run_start, CONST, args.test_run_steps):
        print(f"Iteration: {i}")
        args.headers = i
        # args.specls = i
        _res, _memory = gen(args)
        res.append(_res)
        memory_resident_avg.append(_memory)
        headers.append(i)
        du_opt = subprocess.run(
            "du -sh autogen/pcms",
            capture_output=True,
            shell=True,
        )
        if "K" in du_opt.stdout.decode():
            on_disk_memory.append(float(du_opt.stdout.decode().split("K")[0]) / 1000)
        elif "M" in du_opt.stdout.decode():
            on_disk_memory.append(float(du_opt.stdout.decode().split("M")[0]))
        elif "G" in du_opt.stdout.decode():
            on_disk_memory.append(float(du_opt.stdout.decode().split("G")[0]) * 1000)

    plt.plot(headers, res, color="green")
    res_n = []
    headers_n = []
    args.clang_path = "../llvm-project/build/bin/clang++"
    on_disk_memory_n = []
    memory_resident_avg_n = []
    for i in range(args.test_run_start, CONST, args.test_run_steps):
        print(f"Iteration: {i}")
        args.headers = i
        # args.specls = i
        _res, _memory = gen(args)
        res_n.append(_res)
        headers_n.append(i)
        memory_resident_avg_n.append(_memory)
        du_opt = subprocess.run(
            "du -sh autogen/pcms",
            capture_output=True,
            shell=True,
        )
        if "K" in du_opt.stdout.decode():
            on_disk_memory_n.append(float(du_opt.stdout.decode().split("K")[0]) / 1000)
        elif "M" in du_opt.stdout.decode():
            on_disk_memory_n.append(float(du_opt.stdout.decode().split("M")[0]))
        elif "G" in du_opt.stdout.decode():
            on_disk_memory_n.append(float(du_opt.stdout.decode().split("G")[0]) * 1000)
    plt.plot(headers_n, res_n, color="red")
    plt.savefig("plots/patch_plot.png")
    plt.cla()
    plt.plot(headers_n, on_disk_memory_n, color="red")
    plt.plot(headers, on_disk_memory, color="green")
    plt.savefig("plots/memory_patch_plot.png")
    plt.cla()
    plt.plot(headers_n, memory_resident_avg_n, color="red")
    plt.plot(headers, memory_resident_avg, color="green")
    plt.savefig("plots/resident_memory_plot.png")
    plt.cla()
    try:
        os.remove("plots/data_clang-14.txt")
        os.remove("plots/data_clang_custom_patch.txt")
        os.remove("plots/data_clang_indexes.txt")
        os.remove("plots/data_clang_custom_patch_memory.txt")
        os.remove("plots/data_clang_14_memory.txt")
        os.remove("plots/data_clang_14_memory_resident.txt")
        os.remove("plots/data_clang_custom_memory_resident.txt")
    except:
        pass
    for index, tup in enumerate(zip(res, res_n)):
        i, j = tup
        with open("plots/data_clang-14.txt", "a") as f:
            f.write(str(i) + "\n")
        with open("plots/data_clang_custom_patch.txt", "a") as f:
            f.write(str(j) + "\n")
        with open("plots/data_clang_indexes.txt", "a") as f:
            f.write(str(index) + "\n")
        with open("plots/data_clang_14_memory.txt", "a") as f:
            f.write(str(on_disk_memory[index]) + "\n")
        with open("plots/data_clang_custom_patch_memory.txt", "a") as f:
            f.write(str(on_disk_memory_n[index]) + "\n")
        with open("plots/data_clang_custom_memory_resident.txt", "a") as f:
            f.write(str(memory_resident_avg_n[index]) + "\n")
        with open("plots/data_clang_14_memory_resident.txt", "a") as f:
            f.write(str(memory_resident_avg[index]) + "\n")
