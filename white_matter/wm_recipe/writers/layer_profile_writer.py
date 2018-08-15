class LayerProfileWriter(object):
    def __init__(self, layer_profiles):
        self.layer_profiles = layer_profiles

    def __call__(self, fid):
        l_profiles = self.layer_profiles
        fid.write('layer_profiles:\n')
        prof_name_pat = 'profile_%d'
        prof_k = sorted(l_profiles.patterns.keys())
        prof_layers = [['l1'], ['l23'], ['l4'], ['l5'], ['l6a', 'l6b']]
        for k in prof_k:
            fid.write('\t- name: %s\n' % (prof_name_pat % k))
            fid.write('\t  relative_densities:\n')
            for l, v in zip(prof_layers, l_profiles.patterns[k].transpose()[0]):
                fid.write('\t\t- layers: %s\n' % str(l))
                fid.write('\t\t  value: %f\n' % v)
            fid.write('\n')
        fid.write('\n')
