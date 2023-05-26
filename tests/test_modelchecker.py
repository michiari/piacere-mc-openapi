from mc_openapi.doml_mc import init_model, verify_model

def setup(src, ver):
    dmc = init_model(src, ver)
    verify_model(dmc)

