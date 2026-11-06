"""Unit tests for the Phase 0 categorisation rules (no disk access)."""
from tadla.inventory import Item, classify, file_ext, find_duplicates

MB = 1e6


def make(rel, size=1000, root="C:/x/train", kind="file", ext=None):
    # parse the extension exactly like walk_root() does
    if ext is None:
        ext = file_ext(rel.rsplit("/", 1)[-1])
    return Item(root, rel, kind, ext, int(size), 1, 0.0, False, False)


def test_file_ext():
    assert file_ext("CHIRPS_2017.nc") == ".nc"
    assert file_ext("1.21.0") == ""
    assert file_ext("2022.0.0") == ""
    assert file_ext(".env") == ""
    assert file_ext("x.TIF") == ".tif"


def cat(item):
    return classify(item, 10 * MB)[0]


def test_raw_netcdf_on_d_is_A():
    assert cat(make("CHIRPS_2017.nc", 1.6e9, root="D:/CHIRPS")) == "A"
    assert cat(make("ERA5_2017_reproj.tif", 5e9, root="D:/ERA5")) == "A"
    assert cat(make("NDVI_2017.nc", 5e9, root="D:/NDVI_NetCDF")) == "A"


def test_combined_cubes_and_backups_are_B():
    assert cat(make("combined_data.nc", 143e9, root="D:/COMBINED_DATA")) == "B"
    assert cat(make("combined_with_static.zarr.zip", 80e9, root="D:/COMBINED_DATA")) == "B"
    assert cat(make("clipped_dataset_v5.zarr", 5.8e9, kind="zarr store", ext=".zarr")) == "B"
    assert cat(make("clipped_dataset_v5_BACKUP_before_et0", 2e4, kind="zarr store", ext=".zarr")) == "B"


def test_large_predictions_B_small_tables_C():
    assert cat(make("ndvi_predictions_full.npy", 1.2e9)) == "B"
    assert cat(make("retrain_prepared_data.parquet", 1.8e9)) == "B"
    assert cat(make("ndvi_predictions_1km.npy", 0.5 * MB)) == "C"
    assert cat(make("aggregated_1km_data.parquet", 1 * MB)) == "C"


def test_keep_types_are_C():
    for rel in ["files/infer_1km.py", "ndvi_model_1km.txt", "retrain_metrics.json",
                "figures_fr/fig_IV_1.png", "area.shp", "area.dbf", "Scripts/x.ipynb"]:
        assert cat(make(rel)) == "C", rel


def test_processed_vs_raw_in_pfe_project():
    root = "C:/x/PFE_Project"
    assert cat(make("Data/Processed/GIS/Topography/tadla_dem_10m.tif", 6.8e8, root=root)) == "B"
    assert cat(make("Data/Raw/GIS/Topography/Tadla_DEM.tif", 6.6e7, root=root)) == "A"


def test_junk_is_A():
    assert cat(make("Unconfirmed 989359.crdownload", 16758)) == "A"
    assert cat(make("train/1.21.0", 122)) == "A"
    assert cat(make("train/2022.0.0", 5357)) == "A"
    assert cat(make("__pycache__", 4000, kind="cache", ext="")) == "A"


def test_small_stray_raster_kept_large_gee_tif_A():
    # old ET0 GeoTIFF: producer script missing -> only record, 34 kB -> keep
    assert cat(make("ERA5_FAO56_ET0_Tadla_2017-2023.tif", 34_260)) == "C"
    assert cat(make("some_gee_export.tif", 500 * MB)) == "A"


def test_env_is_kept_and_git_files_not_junk():
    assert cat(make("PFE_Project/.env", 40, ext="")) == "C"
    assert cat(make(".gitignore", 100, ext="")) == "C"


def test_duplicates_need_same_name_and_size():
    a = make("a/fig.png", 500)
    b = make("b/FIG.png", 500)
    c = make("c/fig.png", 501)
    groups = find_duplicates([a, b, c])
    assert len(groups) == 1 and {i.rel for i in groups[0]} == {"a/fig.png", "b/FIG.png"}
