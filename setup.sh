#!/usr/bin/env bash
sudo apt-get update && sudo apt-get -y upgrade
sudo apt install python3-pip python3-tk xvfb
pip3 install setuptools 
pip3 install tensorflow-gpu keras==2.2.2 opencv-python
wget http://host.robots.ox.ac.uk/pascal/VOC/voc2012/VOCtrainval_11-May-2012.tar
wget http://host.robots.ox.ac.uk/pascal/VOC/voc2007/VOCtest_06-Nov-2007.tar
wget http://host.robots.ox.ac.uk/pascal/VOC/voc2007/VOCtrainval_06-Nov-2007.tar
tar -xvf VOCtrainval_11-May-2012.tar
tar -xvf VOCtest_06-Nov-2007.tar
tar -xvf VOCtrainval_06-Nov-2007.tar

# copy these lines for cudnn installation
#sudo cp cuda/include/cudnn.h /usr/local/cuda/include
#sudo cp cuda/lib64/libcudnn* /usr/local/cuda/lib64
#sudo chmod a+r /usr/local/cuda/include/cudnn.h /usr/local/cuda/lib64/libcudnn*

# setup vim.rc
cat > ~/.vimrc << EOF
set nocompatible
filetype indent plugin on
syntax on
set autoindent
set shiftwidth=4
set expandtab
color delek
EOF
