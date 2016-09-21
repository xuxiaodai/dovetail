#!/usr/bin/env python
#
# grakiss.wanglei@huawei.com
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
#


import click
import yaml
import os
import time

import utils.dovetail_logger as dt_logger
import utils.dovetail_utils as dt_utils
logger = dt_logger.Logger('run.py').getLogger()

from container import Container
from testcase import *
from report import *
from conf.dovetail_config import *

def load_scenario(scenario):
    Scenario.load()
    return Scenario.get(SCENARIO_NAMING_FMT % scenario)

def load_testcase():
    Testcase.load()

def run_functest(testcase, container_id):
    sub_cmd = dovetail_config[testcase.script_type()]['testcase']['pre_cmd']
    Container.exec_cmd(container_id, sub_cmd)
    sub_cmd = dovetail_config[testcase.script_type()]['testcase']['exec_cmd'] % testcase.script_testcase()
    Container.exec_cmd(container_id, sub_cmd)

def run_yardstick(testcase, container_id):
    type = testcase.script_type()
    Container.copy_file(os.path.join(os.getcwd(), dovetail_config[type]['shell_dir_name']),\
                        container_id, dovetail_config[type]['shell_dir'])
    if Container.has_build_images[type] == True:
        sub_cmd = dovetail_config[type]['testcase']['test_cmd'] % (testcase.script_testcase(), testcase.name())
    else:
        Container.has_build_images[type] = True
        sub_cmd = dovetail_config[type]['testcase']['build_test_cmd'] % (testcase.script_testcase(), testcase.name())
    Container.exec_cmd(container_id, sub_cmd)
    time.sleep(5)

def run_test(scenario):
    for testcase_name in scenario['testcase_list']:
        logger.info('>>[testcase]: %s' % (testcase_name))
        testcase = Testcase.get(testcase_name)
        run_test = True

        if testcase.exceed_max_retry_times():
            run_test = False

        if testcase.script_result_acquired():
            run_test = False

        if run_test:
            Container.pull_image(testcase.script_type())
            container_id = Container.create(testcase.script_type())
            logger.debug('container id:%s' % container_id)

            if testcase.script_type() == 'functest':
                run_functest(testcase, container_id)
            else:
                run_yardstick(testcase, container_id)

            Container.clean(container_id)

        db_result = Report.get_result(testcase)
        Report.check_result(testcase, db_result)

@click.command()
@click.option('--scenario', default='basic', help='certification scenario')
def main(scenario):
    """Dovetail certification test entry!"""
    logger.info('=======================================')
    logger.info('Dovetail certification: %s!' % scenario)
    logger.info('=======================================')
    load_testcase()
    scenario_yaml = load_scenario(scenario)
    run_test(scenario_yaml)
    Report.generate(scenario_yaml)

if __name__ == '__main__':
    main()
