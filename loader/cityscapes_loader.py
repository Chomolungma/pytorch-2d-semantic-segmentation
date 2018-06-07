import collections
import logging
import os

import numpy as np
import scipy.misc
import torch
import torch.utils.data
import torchvision

import loader.utils

class CityscapesLoader(torch.utils.data.Dataset):

    def __init__(self, args, dataset_params, root, split, imgWidth, imgHeight, imgNorm=True, isTransform=False):

        self.logger = logging.getLogger(__name__)

        self.root = root
        self.split = split
        self.network= args.network.split("_")[0]
        self.dataset_params= dataset_params
        self.img_size = (imgWidth, imgHeight)
        self.img_norm = imgNorm
        self.is_transform = isTransform

        self.class_map = dict(zip(self.dataset_params['VALID_CLASSES'], range(19)))
        self.label_colors = dict(zip(range(19), self.dataset_params['COLORS']))

        self.images_base_path = os.path.join(self.root, 'leftImg8bit', self.split)
        self.labels_base_path = os.path.join(self.root, 'gtFine', self.split)
        self.files = loader.utils.recursive_glob(root=self.images_base_path, suffix='.png')

        if not self.files:
            raise Exception("No files for the requested split {0} were found in {1}".format(
                                self.split,
                                self.images_base_path))

        self.logger.debug("Found {0} images in split {1} on {2}".format(
                len(self.files),
                self.split,
                self.images_base_path))

    def __len__(self):

        return len(self.files)

    def __getitem__(self, index):
        output= []

        img_path_ = self.files[index].rstrip()
        lbl_path_ = os.path.join(self.labels_base_path,
                                    img_path_.split(os.sep)[-2],
                                    os.path.basename(img_path_)[:-15] + 'gtFine_labelIds.png')

        #print("Loading image {0} with labels {1}".format(
        #        img_path_,
        #        lbl_path_))

        img_ = scipy.misc.imread(img_path_)
        img_ = np.array(img_, dtype=np.uint8)

        lbl_ = scipy.misc.imread(lbl_path_)
        lbl_ = self.encode_labels(np.array(lbl_, dtype=np.uint8))
        ind_= np.unique(lbl_)[:-1]

        if self.is_transform:
            img_, lbl_ = self.transform(img_, lbl_)

        
        if self.network == 'unet':
            lbl_rgb_ = torch.from_numpy(self.decode_labels(lbl_.numpy()))
            output = [img_.float(), lbl_.long(), lbl_rgb_.float()]

        if self.network == 'pspnet':
            cls_= np.zeros(self.dataset_params['NUM_CLASSES'])
            cls_[ind_] = 1
            cls_= torch.from_numpy(cls_)

            output= [img_.float(), lbl_.long(), cls_.float()]


        return output
    
    def __repr__(self):

        return "Dataset loader for Cityscapes {0} split with {1} images in {2}...".format(
                    self.split,
                    self.__len__(),
                    self.images_base_path)

    def transform(self, img, lbl):

        img_ = scipy.misc.imresize(img, self.img_size)
        img_ = img_[:,:,::-1]
        img_ = img_.astype(np.float64)
        if self.img_norm:
            img_ = img_.astype(float) / 255.0
        img_ = img_.transpose(2, 0, 1)

        lbl_ = lbl.astype(float)
        lbl_ = scipy.misc.imresize(lbl_, self.img_size, 'nearest', mode='F')

        img_ = torch.from_numpy(img_)
        lbl_ = torch.from_numpy(lbl_)

        return img_, lbl_

    def encode_labels(self, labels):

        lbls_ = np.copy(labels)

        for vc in self.dataset_params['VOID_CLASSES']:
            lbls_[labels == vc] = self.dataset_params['IGNORE_INDEX']
        for vc in self.dataset_params['VALID_CLASSES']:
            lbls_[labels == vc] = self.class_map[vc]

        return lbls_

    def decode_labels(self, labels):

        r_ = labels.copy()
        g_ = labels.copy()
        b_ = labels.copy()

        for l in range(0, self.dataset_params['NUM_CLASSES']):

            r_[labels == l] = self.label_colors[l][0]
            g_[labels == l] = self.label_colors[l][1]
            b_[labels == l] = self.label_colors[l][2]

        rgb_ = np.zeros((labels.shape[0], labels.shape[1], 3))
        rgb_[:,:,0] = r_ / 255.0
        rgb_[:,:,1] = g_ / 255.0
        rgb_[:,:,2] = b_ / 255.0
        
        return rgb_

    def decode_labels_batch(self, labels):

        r_ = labels.copy()
        g_ = labels.copy()
        b_ = labels.copy()

        for l in range(self.dataset_params['NUM_CLASSES']):

            r_[labels == l] = self.label_colors[l][0]
            g_[labels == l] = self.label_colors[l][1]
            b_[labels == l] = self.label_colors[l][2]

        rgb_ = np.zeros((labels.shape[0], labels.shape[1], labels.shape[2],  3))

        rgb_[:,:,:,0] = r_ / 255.0
        rgb_[:,:,:,1] = g_ / 255.0
        rgb_[:,:,:,2] = b_ / 255.0

        return torch.from_numpy(rgb_)
