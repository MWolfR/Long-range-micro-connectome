#!/usr/bin/env python
import numpy
import logging
from white_matter.wm_recipe.parcellation import RegionMapper
from white_matter.wm_recipe.projection_mapping import VoxelNodeBaryMapper, VoxelArrayBaryMapper


logging.basicConfig(level=1)
info_log = logging.getLogger(__file__)


def make_mapper(cfg):
    import mcmodels
    if cfg['class'] == 'VoxelNodeBaryMapper':
        cls = VoxelNodeBaryMapper
    elif cfg['class'] == 'VoxelArrayBaryMapper':
        cls = VoxelArrayBaryMapper
    else:
        raise Exception("Unknown mapper class: %s" % cfg['class'])
    cache = mcmodels.core.VoxelModelCache(
        manifest_file=cfg["cache_manifest"])
    obj = cls.from_cache(cache, custom_flatmap=cfg.get('flatmap', None))
    return obj


def main(cfg, obj, src):
    import h5py
    import os
    from matplotlib import pyplot as plt
    mpr = RegionMapper(cfg["BrainParcellation"])
    cfg = cfg["ProjectionMapping"]

    target_args = cfg["target_args"]
    pp_use = cfg["pp_use"]
    pp_display = cfg["pp_display"]
    prepare_args = cfg["prepare_args"]
    fit_args = cfg["fit_args"]
    flatmap_str = cfg.get("flatmap", "Allen Dorsal Flatmap")
    if "cre" in prepare_args and prepare_args["cre"] == "None":
        print("Using both cre positive and negative experiments")
        prepare_args["cre"] = None

    out_plots = cfg["plot_dir"]
    if not os.path.exists(out_plots):
        os.makedirs(out_plots)

    out_h5_fn = cfg["h5_fn"]
    if not os.path.exists(os.path.split(out_h5_fn)[0]):
        os.makedirs(os.path.split(out_h5_fn)[0])
    if os.path.exists(out_h5_fn):
        h5 = h5py.File(out_h5_fn, 'r+')
    else:
        h5 = h5py.File(out_h5_fn, 'w')

    obj.prepare_for_source(src, interactive=False, **prepare_args)

    grp = h5.require_group(str(src))
    grp_coords = grp.require_group('coordinates')
    grp_coords.attrs['base_coord_system'] = flatmap_str # TODO: make dataset instead of attribute
    grp_coords.require_dataset('x', (3,), float, data=obj._bary._coords[0])
    grp_coords.require_dataset('y', (3,), float, data=obj._bary._coords[1])
    grp = grp.require_group('targets')

    for tgt in mpr.region_names:
        try:
            tgt_grp = grp.require_group(tgt)
            tgt_plots = os.path.join(out_plots, str(src), str(tgt))
            if not os.path.exists(tgt_plots):
                os.makedirs(tgt_plots)
            if 'coordinates/base_coord_system' in tgt_grp:
                info_log.info("%s/%s already present. Skipping..." %
                              (str(src), str(tgt)))
                continue
            res, map_var, overlaps, error, ax1, ax2 = obj.make_target_region_coordinate_system(tgt,
                                    target_args=target_args, pp_use=pp_use,
                                    pp_display=pp_display, fit_args=fit_args, draw=True)
            ax1.figure.savefig(os.path.join(tgt_plots, ('%s_data' % str(tgt)) + cfg["plot_extension"]))
            ax2.figure.savefig(os.path.join(tgt_plots, ('%s_model' % str(tgt)) + cfg["plot_extension"]))
            plt.close('all')
            tgt_grp.create_dataset('coordinates/base_coord_system', data=flatmap_str)
            tgt_grp.create_dataset('coordinates/x', data=res._coords[0])
            tgt_grp.create_dataset('coordinates/y', data=res._coords[1])
            tgt_grp.create_dataset('mapping_variance', data=[map_var])
            tgt_grp.create_dataset('error', data=[error])
            tgt_grp.create_dataset('overlaps', data=overlaps)
            if isinstance(obj, VoxelNodeBaryMapper):
                N = numpy.all(~numpy.isnan(obj._exp_cols), axis=1).sum()
                tgt_grp.create_dataset('n_experiments', data=[N])
            h5.flush()
        except Exception:
            print("Trouble with %s/%s" % (str(src), str(tgt)))
            continue
    h5.close()


if __name__ == "__main__":
    import sys
    import os
    from white_matter.utils.paths_in_config import path_local_to_cfg_root
    from white_matter.utils.data_from_config import read_config
    cfg_file = sys.argv[1]
    cfg = read_config(cfg_file)
    cfg["ProjectionMapping"]["cfg_root"] = cfg["cfg_root"]
    path_local_to_cfg_root(cfg["ProjectionMapping"], ["cache_manifest", "h5_fn"])
    obj = make_mapper(cfg["ProjectionMapping"])
    if len(sys.argv) > 2:
        main(cfg, obj, sys.argv[2])
    else:
        M = RegionMapper(cfg_file=cfg_file)
        for src in M.region_names:
            main(cfg, obj, src)
