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


# def createSample(listp, dictp, zcenter):
#     # creates a sample from inputbox, imageDict, zcenter
#     listToReturn = []
#     slicesfound = 0  # for debugging
#     centerZIndex = None
#     # create volume and list of minz maxz
#     if zcenter in dictp:
#         centerZIndex = list(dictp.keys()).index(zcenter)
#     minZIndex = int(centerZIndex - Zsize / 2)
#     maxZIndex = int(centerZIndex + Zsize / 2)
#     if minZIndex < 0 or maxZIndex > len(dictp):  # for debugging
#         print("Slice out of range")
#         slicefail = True
#         return ([], [])
#     zlist = list(dictp.items())
#     minzbound = float(zlist[minZIndex][0])
#     maxzbound = float(zlist[maxZIndex][0])
#     for j in range(minZIndex, maxZIndex):
#         value = zlist[j][1]
#         part = np.array(value)
#         slicewanted = part[listp[0][0]:listp[0][1], listp[1][0]:listp[1][1]]
#         listToReturn.append(slicewanted)
#     return (listToReturn, [minzbound, maxzbound])
#
#
# def CreateTranslatedPositive(listp, dictp, zcenter):
#     # boxXY, imageDict, centerZ
#     # Randomized translation:
#     xShift = random.randint(-10, 10)
#     yShift = random.randint(-10, 10)
#     zShift = random.randint(-4, 4)
#
#     listp[0][0] += xShift
#     listp[0][1] += xShift
#     listp[1][0] += yShift
#     listp[1][1] += yShift
#
#     listToReturn = []
#     slicesfound = 0  # for debugging
#     # check z translate range
#     centerZIndex = None
#     if zcenter in dictp:
#         centerZIndex = list(dictp.keys()).index(zcenter)
#         centerZIndex += zShift
#     minZIndex = int(centerZIndex - Zsize / 2)
#     maxZIndex = int(centerZIndex + Zsize / 2)
#     if minZIndex < 0 or maxZIndex > len(dictp):  # for debugging
#         print("Slice out of range")
#         slicefail = True
#         return ([], [])
#     zlist = list(dictp.items())
#     minzbound = float(zlist[minZIndex][0])
#     maxzbound = float(zlist[maxZIndex][0])
#     # append slices to create volume
#     for k in range(minZIndex, maxZIndex):
#         value = zlist[k][1]
#         part = np.array(value)
#         slicewanted = part[listp[0][0]:listp[0][1], listp[1][0]:listp[1][1]]
#         listToReturn.append(slicewanted)
#     # return volume, [minz, maxz]
#     return (listToReturn, [minzbound, maxzbound])


def getZindices(imageDict, minz, maxz):
    minZIndex = list(imageDict.keys()).index(minz)
    maxZIndex = list(imageDict.keys()).index(maxz)
    if minZIndex < 0 or maxZIndex > len(imageDict):  # for debugging
        print("Slice out of range")
        slicefail = True
        print('z index error out of bounds')
        return None, None
    return list(imageDict.keys()).index(minz), list(imageDict.keys()).index(maxz)


# functions
# def createNegative(listp, dictp, slthick):
#     # listp = exclude_set, dictp = imageDict, slice thickness
#     while (True):
#         # get xmin and y min
#         xmin = random.randint(0, 512 - Xsize)
#         ymin = random.randint(0, 512 - Ysize)
#         # get z from valid zs
#         allZs = list(dictp.keys())
#         validZs = allZs[int(0 + .5 * Zsize): int(len(allZs) - (.5 * Zsize))]
#         zcenter = random.choice(validZs)
#         zmin = zcenter - slthick * .5 * Zsize
#         intersect = False
#         for box in listp:
#             xcoords = box[0]
#             ycoords = box[1]
#             zcoords = box[2]
#             # check if xmin, ymin, zmin, in range of nodule
#             if xmin in range(xcoords[0] - Xsize, xcoords[1]):
#                 if ymin in range(ycoords[0] - Ysize, ycoords[1]):
#                     if zmin >= zcoords[0] - slthick * Zsize and zmin <= zcoords[1]:
#                         intersect = True
#                         break
#         # if no intersections, add a negative sample
#         if (not intersect):
#             samplex = [xmin, xmin + Xsize]
#             sampley = [ymin, ymin + Ysize]
#             inputBox = [samplex, sampley]
#             return createSample(inputBox, dictp, zcenter)


# init main
# load database information
fileextnesion = '.pickle'
loadedData = None

# load excel info
x1 = pd.ExcelFile("noduleDimensions.xlsx")
allNodules = x1.parse(x1.sheet_names[0])
# allNodules = df[ df["SliceThickness"] <= 2.5] df = df.drop(df[df.score < 50].index)
allNodules = allNodules.sort_values(['SeriesID'])

IDs = list(allNodules["SeriesID"].drop_duplicates())
# validation_set = IDs[-120:-1]
# validation_set.append(IDs[-1])
validation_set = []
# print(sorted(validation_set) == validation_set); exit()

nodulesToUse = x1.parse(x1.sheet_names[2])
noduleSet = set(nodulesToUse["NoduleID"])
del nodulesToUse
del x1

print(len(set(allNodules["SeriesID"]))); exit()
print(len(IDs)); exit()

# save all nodules in numpy form
for id in IDs:
    print(id)
    with open(savePath + str(id), "rb") as f:
        loadedData = pickle.load(f)
        imageDict = OrderedDict(sorted(loadedData.items(), key=lambda t: t[0]))
        npmatrix = np.array(list(imageDict.values()))

        npmatrix = np.transpose(npmatrix, (1, 2, 0))
        np.save(savePath + str(id) + '.npy', npmatrix)
        print(npmatrix.shape)

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
# print ('val_set index',[list(allNodules['SeriesID']).index(validation_set[i]) for i in range(len(validation_set))])
# print ('all_set index',[list(allNodules['SeriesID']).index(allNodules['SeriesID'][i]) for i in range(len(list(allNodules['SeriesID'])))])
# iterate thru nodules w/ repetitions of ids


for i in range(len(allNodules)):
    # check slice thickness <= 2.5
    if allNodules["SliceThickness"][i] <= 2.5:
        # print('st <= 2.5')
        nodeID = allNodules["NoduleID"][i]
        seriesID = allNodules["SeriesID"][i]

        if prevID != seriesID:

            counter += 1
            # check seriesID repeat
            if prevID in seriesIDset:
                print("Repeat Series ID: " + str(prevID))
            else:
                seriesIDset.add(prevID)
            # print progress 
            if counter % 100 == 0:
                print(str(counter) + " Done")
            # open seriesID pickle file from Data
            tempdict = pickle.load(open(savePath + str(seriesID), "rb"))
            # sort by z, imageDict will Dict w/ keys=z value, values=2d ct scan
            imageDict = OrderedDict(sorted(tempdict.items(), key=lambda t: t[0]))
            del tempdict

        # processing positive volumes
        prevID = seriesID
        if nodeID in noduleSet:
            minZind, maxZind = getZindices(imageDict, allNodules["minimumZ"][i], allNodules["maximumZ"][i])
            if slicefail:
                print("Slices out of range: " + str(nodeID))
                slicefail = False
                takeNegativeSample = False

            positivelist.append([str(seriesID),
                                 str(allNodules["minimumX"][i]), str(allNodules["maximumX"][i]),
                                 str(allNodules["minimumY"][i]), str(allNodules["maximumY"][i]),
                                 str(minZind), str(maxZind),
                                 'pos'])

print("Neg Parse fails: " + str(len(pfailedneglist)))
print("Neg Size fails: " + str(len(sfailedneglist)))
print("Pos Parse fails: " + str(len(pfailedposlist)))
print("Pos Size fails: " + str(len(sfailedposlist)))

print("Positive samples: " + str(len(positivelist)))
print("Negative samples: " + str(len(negativelist)))

# save poslist to file
with open("data.txt", 'w') as f:
    for line in positivelist:
        f.write(','.join(line) + '\n')

# print (counterx)
# print (counterzeta)
# with open(savePath + "PositiveAugmented.pickle", 'wb') as handle:
#     # x_train = np.array(positivelist)
#     # x_train = np.clip(x_train, bottom_threshold, top_threshold)
#     # x_train = x_train.reshape(
#     #    (x_train.shape[0], x_train.shape[1], x_train.shape[2], x_train.shape[3], 1))
#     # minx = np.amin(x_train)
#     # halfRange = (np.amax(x_train) - minx) / 2.0
#     # if minx < 0:
#     #    x_train -= minx
#     # x_train = (x_train - halfRange) / halfRange
#     # pickle.dump(x_train, handle, protocol=pickle.HIGHEST_PROTOCOL)
#     pickle.dump(positivelist, handle, protocol=pickle.HIGHEST_PROTOCOL)

# with open(savePath + "NegativeAugmented.pickle", 'wb') as handle:
#     pickle.dump(negativelist, handle, protocol=pickle.HIGHEST_PROTOCOL)
#
# with open(savePath + "ValidationAugmented.pickle", 'wb') as handle:
#     pickle.dump(validation_set, handle, protocol=pickle.HIGHEST_PROTOCOL)
#
# with open(savePath + "PositiveerrorsAugmented.pickle", 'wb') as handle:
#     pickle.dump(pfailedposlist, handle, protocol=pickle.HIGHEST_PROTOCOL)
#     pickle.dump(sfailedposlist, handle, protocol=pickle.HIGHEST_PROTOCOL)
#
# with open(savePath + "NegativeerrorsAugmented.pickle", 'wb') as handle:
#     pickle.dump(pfailedneglist, handle, protocol=pickle.HIGHEST_PROTOCOL)
#     pickle.dump(sfailedneglist, handle, protocol=pickle.HIGHEST_PROTOCOL)
#
# with open(savePath + "ValidationIDs4.pickle", 'wb') as handle:
#     pickle.dump(validation_set, handle, protocol=pickle.HIGHEST_PROTOCOL)
