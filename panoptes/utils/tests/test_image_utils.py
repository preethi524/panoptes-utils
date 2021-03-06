import os
import numpy as np
import pytest
import shutil
import tempfile

from astropy.nddata import Cutout2D

from panoptes.utils import images as img_utils
from panoptes.utils import error


def test_make_images_dir(save_environ):
    assert img_utils.make_images_dir()

    # Invalid parent directory for 'images'.
    os.environ['PANDIR'] = '/dev/null/'
    with pytest.warns(UserWarning):
        assert img_utils.make_images_dir() is None

    # Valid parents for 'images' that need to be created.
    with tempfile.TemporaryDirectory() as tmpdir:
        parent = os.path.join(tmpdir, 'some', 'dirs')
        imgdir = os.path.join(parent, 'images')
        os.environ['PANDIR'] = parent
        assert img_utils.make_images_dir() == imgdir


def test_crop_data():
    ones = np.ones((201, 201))
    assert ones.sum() == 40401.

    cropped01 = img_utils.crop_data(ones, verbose=False)  # False to exercise coverage.
    assert cropped01.sum() == 40000.

    cropped02 = img_utils.crop_data(ones, verbose=True, box_width=10)
    assert cropped02.sum() == 100.

    cropped03 = img_utils.crop_data(ones, verbose=True, box_width=6, center=(50, 50))
    assert cropped03.sum() == 36.

    # Test the Cutout2D object
    cropped04 = img_utils.crop_data(ones,
                                    verbose=True,
                                    box_width=20,
                                    center=(50, 50),
                                    data_only=False)
    assert isinstance(cropped04, Cutout2D)
    assert cropped04.position_original == (50, 50)

    # Box is 20 pixels wide so center is at 10,10
    assert cropped04.position_cutout == (10, 10)


def test_make_pretty_image(solved_fits_file, tiny_fits_file, save_environ):
    # Not a valid file type (can't automatically handle .fits.fz files).
    with pytest.warns(UserWarning, match='File must be'):
        assert not img_utils.make_pretty_image(solved_fits_file)

    # Make a dir and put test image files in it.
    with tempfile.TemporaryDirectory() as tmpdir:
        fz_file = os.path.join(tmpdir, os.path.basename(solved_fits_file))
        fits_file = os.path.join(tmpdir, os.path.basename(tiny_fits_file))
        # TODO Add a small CR2 file to our sample image files.

        # Can't operate on a non-existent files.
        with pytest.warns(UserWarning, match="File doesn't exist"):
            assert not img_utils.make_pretty_image(fits_file)

        # Copy the files.
        shutil.copy(solved_fits_file, tmpdir)
        shutil.copy(tiny_fits_file, tmpdir)

        # Not a valid file type (can't automatically handle fits.fz files).
        with pytest.warns(UserWarning):
            assert not img_utils.make_pretty_image(fz_file)

        # Can handle the fits file, and creating the images dir for linking
        # the latest image.
        imgdir = os.path.join(tmpdir, 'images')
        assert not os.path.isdir(imgdir)
        os.environ['PANDIR'] = tmpdir

        pretty = img_utils.make_pretty_image(fits_file, link_latest=True)
        assert pretty
        assert os.path.isfile(pretty)
        assert os.path.isdir(imgdir)
        latest = os.path.join(imgdir, 'latest.jpg')
        assert os.path.isfile(latest)
        os.remove(latest)
        os.rmdir(imgdir)

        # Try again, but without link_latest.
        pretty = img_utils.make_pretty_image(fits_file, title='some text')
        assert pretty
        assert os.path.isfile(pretty)
        assert not os.path.isdir(imgdir)


@pytest.mark.skipif(
    "TRAVIS" in os.environ and os.environ["TRAVIS"] == "true",
    reason="Skipping this test on Travis CI.")
def test_make_pretty_image_cr2_fail():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpfile = os.path.join(tmpdir, 'bad.cr2')
        with open(tmpfile, 'w') as f:
            f.write('not an image file')
        with pytest.raises(error.InvalidCommand):
            img_utils.make_pretty_image(tmpfile, title='some text', link_latest=False, verbose=True)
        with pytest.raises(error.InvalidCommand):
            img_utils.make_pretty_image(tmpfile, verbose=True)
