from importlib.resources import files
from mc_openapi.doml_mc import init_model, verify_model
from pathlib import Path

from mc_openapi.doml_mc.intermediate_model.metamodel import DOMLVersion

doml_test_dir = files(package='tests') / 'doml'

def run(src, ver):
    dmc = init_model(src, ver)
    return verify_model(dmc)

def test_domlx_models_by_version(subtests):
    i = 0
    for doml_ver_dir in [ver for ver in doml_test_dir.iterdir() if ver.name != 'CaseStudies']:
        doml_ver = doml_ver_dir.name
        domlx_files = [f for f in doml_ver_dir.iterdir() if f.is_file() and f.name.endswith('.domlx')]
        for domlx in domlx_files:
            with open(domlx, "rb") as f:
                domlx_file = f.read()
                assert_ver = DOMLVersion.get(doml_ver)
                res = run(domlx_file, assert_ver)
                try:
                    assert_result = OUTPUT[doml_ver][domlx.name]
                    i += 1
                except:
                    pass
            if assert_result:
                with subtests.test(msg=f"{doml_ver}/{domlx.name}", i=i):
                        assert assert_result == res['result'].name
                        assert assert_ver.name == res['doml_version']

OUTPUT = {
    'v2.0': {
        'faas.domlx': 'unsat',
        'nginx-openstack_v2.0.domlx': 'sat',
        'nginx-openstack_v2.0_wrong_all_concrete_map_something.domlx': 'unsat',
        'nginx-openstack_v2.0_wrong_all_infrastructure_elements_deployed.domlx': 'unsat',
        'nginx-openstack_v2.0_wrong_iface_uniq.domlx': 'unsat',
        'nginx-openstack_v2.0_wrong_software_package_iface_net.domlx': 'unsat',
        'nginx-openstack_v2.0_valid_mem_req.domlx': 'sat',
        'nginx-openstack_v2.0_wrong_nginx_source_code.domlx': 'sat',
        'openstack_template.domlx': 'unsat',
        'saas.domlx': 'sat',
        'saas_https_no_attrs.domlx': 'sat',
        'saas_no_https_rule.domlx': 'sat',
        'saas_wrong_no_iface_sg.domlx': 'sat',
        'nginx-openstack_v2.0_wrong_vm_has_iface.domlx': 'unsat',
        'nginx-openstack_v2.0_wrong_all_software_components_deployed.domlx': 'unsat'
    },
    'v2.1': {
        'faas.domlx': 'unsat',
        'nginx-aws-ec2.domlx': 'sat'
    },
    'v2.2': {
        'faas.domlx': 'unsat',
        'iot_simple_app.domlx': 'unsat',
        'nginx-aws-ec2.domlx': 'sat',
        'nginx_func_req2_unsat.domlx': 'unsat',
        'nginx_func_req2_unsat_neg.domlx': 'unsat',
        'nginx_func_req_neg.domlx': 'sat',
        'nginx-csp-compatibility-test.domlx': 'sat',
        'nginx_func_req.domlx': 'sat',
        'nginx_flags.domlx': 'sat'
    },
    'v2.3': {

    },
}