# tumor-detection
Tumor-Detection

Please install PyTorch Cuda version & requirements.txt to run the code.

### A 3D segmentation task:

`python3 train3d.py --task brats --split all --bs 2 --maxiter 10000 --randscale 0.1 --net segtran --attractors 1024 --translayers 1`

`python3 test3d.py --task brats --split all --bs 5 --ds 2019valid --net segtran --attractors 1024 --translayers 1 --cpdir ../model/segtran-brats-2019train-01170142 --iters 8000`

*Arguments:*

`--net`: which type of model to use. Currently three 3D segmentation models can be chosen from. `unet`: 3D U-Net. `vnet`: V-Net. `segtran`: Squeeze-and-Expansion transformer for segmentation.

`--bb`: the type of CNN backbone for `segtran`. A commonly used 3D backbone is `i3d` (default).

`--attractors`: the number of attractors in the Squeezed Attention Block. 

To save GPU RAM, 3D tasks usually only use one transformer layer, i.e., `--translayers 1`.

### Accuracy achieved for BRATS 2019
![image](https://github.com/HarshDutt17/tumor-detection/assets/78022802/64c5b9d1-fd11-43c1-b739-26b5c1ebac23)


### Acknowledgement

The "receptivefield" folder is from https://github.com/fornaxai/receptivefield/, with minor edits and bug fixes.

The "efficientnet" folder is from https://github.com/lukemelas/EfficientNet-PyTorch, with minor customizations.

The "networks/setr" folder is a slimmed-down version of https://github.com/fudan-zvg/SETR/, with a few custom config files.

There are a few baseline models under networks/ which were originally implemented in various github repos. Here I won’t acknowlege them individually.

Some code under "dataloaders/" (esp. 3D image preprocessing) was borrowed from https://github.com/yulequan/UA-MT.
