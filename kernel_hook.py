import jinja2
import glob
import os
import shutil
import copy
template ="""
title Arch Linux
linux b506d67aecf64562a572222fc7bc43b3/vmlinuz
initrd b506d67aecf64562a572222fc7bc43b3/initrd.img
options cryptdevice=UUID=c7de0d39-7073-4bbb-84fb-b8c72d0a20da:e15volume root=/dev/mapper/e15volume-root quiet rw
"""
systemd_boot_template = """
title Debian{{postfix}}
linux {{efi_path_linux}}
initrd {{efi_path_initrd}}
options cryptdevice=UUID=c7de0d39-7073-4bbb-84fb-b8c72d0a20da:e15volume root=/dev/mapper/e15volume-root quiet rw
"""

efi_mount_point = "/boot/efi"
efi_kernel_install_prefix = "/"

template_base_dir = jinja2.Template('{{efi_kernel_install_prefix}}{{machine_id}}{{postfix}}')
template_linux_name = jinja2.Template('vmlinuz')
template_initrd_name = jinja2.Template('initrd.img')
template_systemd_boot = jinja2.Template(systemd_boot_template)
template_systemd_boot_file_path = jinja2.Template("/loader/entries/{{machine_id}}{{postfix}}.conf")

def get_postfix_path(path):
    out = {}
    globbed_path = glob.glob(f"{path}*")
    for file_path in globbed_path:
        postfix = file_path.partition(path)[2]
        out[postfix] = file_path
    return out

def get_kernel_files():
    linux_prefix = get_postfix_path("/boot/vmlinuz")
    initrd_prefix = get_postfix_path("/boot/initrd.img")
    sharedkeys = set(linux_prefix.keys()).intersection(initrd_prefix)
    out = {}
    for key in sharedkeys:
        out[key] = {
            "linux" : linux_prefix[key],
            "initrd" : initrd_prefix[key]
        }
    return out


def install_file(cfg, src_path, filename):

    base_dir = template_base_dir.render(**cfg)

    print(f"efi_mount_point={efi_mount_point}")

    mounted_base_dir = efi_mount_point + base_dir
    print(f"mounted_base_dir={mounted_base_dir}")
    if not os.path.exists(mounted_base_dir):
        os.makedirs(mounted_base_dir)
    filepath = base_dir + os.path.sep + filename
    mounted_filepath = efi_mount_point + os.path.sep +  filepath
    if not os.path.exists(mounted_filepath):
        shutil.copy(src_path, mounted_filepath)
    return filepath



def install_kernels(*, machine_id):
    kf = get_kernel_files()
    cfg = {
        "efi_mount_point" : efi_mount_point,
        "efi_kernel_install_prefix" : efi_kernel_install_prefix,
        "machine_id" : machine_id
    }

    template_base_dir = jinja2.Template('{{efi_kernel_install_prefix}}{{machine_id}}{{postfix}}')

    for postfix, params in kf.items():
        localcfg = copy.deepcopy(cfg)
        localcfg["postfix"] = postfix
        linux_filename = template_linux_name.render(**localcfg)
        localcfg["efi_path_linux"] = install_file(localcfg, params.get("linux"), linux_filename)
        if "initrd" in params:
            initrd_filename = template_initrd_name.render(**localcfg)
            localcfg["efi_path_initrd"] = install_file(localcfg, params.get("initrd"), initrd_filename)


        bootfile_path = efi_mount_point + template_systemd_boot_file_path.render(localcfg)
        if not os.path.exists(bootfile_path):
            bootfile = template_systemd_boot.render(localcfg)
            with open(bootfile_path, 'w') as writer:
                writer.write(bootfile)






def main():
    with open("/etc/machine-id") as f:
        content = f.read().strip()
    install_kernels(machine_id=content)




main()