# -*- coding: utf-8 -*-
"""
Created on Mon Jul 24 12:03:55 2017

@author: SMAHESH
"""

# Code to make augmented positive and negative examples

# CNNinputDataExtractionV3.py
# Extracts augmented positive and negative subvolumes
# Requires: dictinaries of images data, nodulDimensions
# Produces:
#    - List of 5800 negative subvolumes (10 from each scan, chosen randomly)
#    - List of 5425 positive subvolumes (7 per nodule - translated, rotated, and reflected)
#    - List of Series IDs set aside for validation
#    - List of nodules where the coordinate could not be found in the image dictionary
#    - List of series IDs where a nodule coordinate couldn’t be found in the image dictionary
import pickle
import gc
import pandas as pd
from collections import OrderedDict
import numpy as np
import random

random.seed(10)

# global / box sizes (40,40,18)
Xsize = 40
Ysize = 40
Zsize = 18

counter = 0
counterzeta = 0
savePath = '/home/cc/Data/'
top_threshold = 2446
bottom_threshold = -1434

print("Start")
slicefail = False


def getZindices(imageDict, minz, maxz):
    try:
        minZIndex = list(imageDict.keys()).index(minz)
        maxZIndex = list(imageDict.keys()).index(maxz)
    except:
        pass
    if maxz not in imageDict.keys() or minz not in imageDict.keys():  # for debugging
        slicefail = True
        print('z index error out of bounds')
        return None, None, True
    return list(imageDict.keys()).index(minz), list(imageDict.keys()).index(maxz), False


fileextnesion = '.pickle'
loadedData = None

# load excel info
x1 = pd.ExcelFile("noduleDimensions.xlsx")
allNodules = x1.parse(x1.sheet_names[0])
# allNodules = df[ df["SliceThickness"] <= 2.5] df = df.drop(df[df.score < 50].index)
allNodules = allNodules.sort_values(['SeriesID'])

IDs = list(allNodules["SeriesID"].drop_duplicates())
validation_set = []

nodulesToUse = x1.parse(x1.sheet_names[2])
noduleSet = set(nodulesToUse["NoduleID"])
del nodulesToUse
del x1

# save all nodules in numpy form, uncomment if need to reprocess
# for id in IDs:
#     print(id)
#     with open(savePath + str(id), "rb") as f:
#         loadedData = pickle.load(f)
#         imageDict = OrderedDict(sorted(loadedData.items(), key=lambda t: t[0]))
#         npmatrix = np.array(list(imageDict.values()))
#
#         npmatrix = np.transpose(npmatrix, (1, 2, 0))
#         np.save(savePath + str(id) + '.npy', npmatrix)
#         print(npmatrix.shape)

# headerList = list(allNodules)
prevID = None
exclude_set = []
positivelist = []
sfailedposlist = []
pfailedposlist = []
negativelist = []
sfailedneglist = []
pfailedneglist = []
tempdict = None
imageDict = None
takeNegativeSample = True
seriesIDset = set()
counterx = 0


for i in range(len(allNodules)):
    print(i)
    # check slice thickness <= 2.5
    #if allNodules["SliceThickness"][i] <= 2.5:
    nodeID = allNodules["NoduleID"][i]
    seriesID = allNodules["SeriesID"][i]

    # processing positive volumes
    if nodeID in noduleSet:
        # open seriesID pickle file from Data
        tempdict = pickle.load(open(savePath + str(seriesID), "rb"))
        # sort by z, imageDict will Dict w/ keys=z value, values=2d ct scan
        imageDict = OrderedDict(sorted(tempdict.items(), key=lambda t: t[0]))
        del tempdict

        print(allNodules["minimumZ"][i], allNodules["maximumZ"][i])
        print(min(imageDict.keys()), max(imageDict.keys()))

        minZind, maxZind, slicefail = getZindices(imageDict, allNodules["minimumZ"][i], allNodules["maximumZ"][i])
        if slicefail:
            print("Slices out of range: " + str(nodeID))
            slicefail = False
        else: 
            positivelist.append([str(seriesID),
                str(allNodules["minimumX"][i]), str(allNodules["maximumX"][i]),
                str(allNodules["minimumY"][i]), str(allNodules["maximumY"][i]),
                str(minZind), str(maxZind), 'pos'])

# save poslist to file
with open("data.txt", 'w') as f:
    for line in positivelist:
        f.write(','.join(line) + '\n')
