#! /usr/bin/env python
# encoding: utf-8
# WARNING! Do not edit! http://waf.googlecode.com/git/docs/wafbook/single.html#_obtaining_the_waf_file

import objcopy
import pebble_sdk_gcc
def generate_bin_file(task_gen,bin_type,elf_file,has_pkjs,has_worker):
	platform_build_node=task_gen.bld.path.get_bld().find_node(task_gen.bld.env.BUILD_DIR)
	packaged_files=[elf_file]
	resources_file=None
	if bin_type!='worker':
		resources_file=platform_build_node.find_or_declare('app_resources.pbpack')
		packaged_files.append(resources_file)
	raw_bin_file=platform_build_node.make_node('pebble-{}.raw.bin'.format(bin_type))
	bin_file=platform_build_node.make_node('pebble-{}.bin'.format(bin_type))
	task_gen.bld(rule=objcopy.objcopy_bin,source=elf_file,target=raw_bin_file)
	pebble_sdk_gcc.gen_inject_metadata_rule(task_gen.bld,src_bin_file=raw_bin_file,dst_bin_file=bin_file,elf_file=elf_file,resource_file=resources_file,timestamp=task_gen.bld.env.TIMESTAMP,has_pkjs=has_pkjs,has_worker=has_worker)
	return bin_file
