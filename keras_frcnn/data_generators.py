from __future__ import absolute_import
import numpy as np
import cv2
import random
import copy
import threading
import itertools


def augment(img_data, C, augment=True):
    assert 'filepath' in img_data
    assert 'bboxes' in img_data
    assert 'width' in img_data
    assert 'height' in img_data

    if C.use3d == False:
        img_data_aug = copy.deepcopy(img_data)
        img = cv2.imread(img_data_aug['filepath'])

        if augment:
            rows, cols = img.shape[:2]

            if C.use_horizontal_flips and np.random.randint(0, 2) == 0:
                img = cv2.flip(img, 1)
                for bbox in img_data_aug['bboxes']:
                    x1 = bbox['x1']
                    x2 = bbox['x2']
                    bbox['x2'] = cols - x1
                    bbox['x1'] = cols - x2

            if C.use_vertical_flips and np.random.randint(0, 2) == 0:
                img = cv2.flip(img, 0)
                for bbox in img_data_aug['bboxes']:
                    y1 = bbox['y1']
                    y2 = bbox['y2']
                    bbox['y2'] = rows - y1
                    bbox['y1'] = rows - y2

            if C.rot_90:
                angle = np.random.choice([0, 90, 180, 270], 1)[0]
                if angle == 270:
                    img = np.transpose(img, (1, 0, 2))
                    img = cv2.flip(img, 0)
                elif angle == 180:
                    img = cv2.flip(img, -1)
                elif angle == 90:
                    img = np.transpose(img, (1, 0, 2))
                    img = cv2.flip(img, 1)
                elif angle == 0:
                    pass

                for bbox in img_data_aug['bboxes']:
                    x1 = bbox['x1']
                    x2 = bbox['x2']
                    y1 = bbox['y1']
                    y2 = bbox['y2']
                    if angle == 270:
                        bbox['x1'] = y1
                        bbox['x2'] = y2
                        bbox['y1'] = cols - x2
                        bbox['y2'] = cols - x1
                    elif angle == 180:
                        bbox['x2'] = cols - x1
                        bbox['x1'] = cols - x2
                        bbox['y2'] = rows - y1
                        bbox['y1'] = rows - y2
                    elif angle == 90:
                        bbox['x1'] = rows - y2
                        bbox['x2'] = rows - y1
                        bbox['y1'] = x1
                        bbox['y2'] = x2
                    elif angle == 0:
                        pass

        img_data_aug['width'] = img.shape[1]
        img_data_aug['height'] = img.shape[0]
        return img_data_aug, img
    else:
        img_data_aug = copy.deepcopy(img_data)
        img = np.load(img_data_aug['filepath'])
        img_data_aug['width'] = img.shape[1]
        img_data_aug['height'] = img.shape[0]
        img_data_aug['depth'] = img.shape[2]
        return img_data_aug, img

def union(au, bu, area_intersection):
    if len(au) == 4:
        area_a = (au[2] - au[0]) * (au[3] - au[1])
        area_b = (bu[2] - bu[0]) * (bu[3] - bu[1])
        area_union = area_a + area_b - area_intersection
        return area_union
    else:
        area_a = (au[3] - au[0]) * (au[4] - au[1]) * (au[5] - au[2])
        area_b = (bu[3] - bu[0]) * (bu[4] - bu[1]) * (au[5] - au[2])
        area_union = area_a + area_b - area_intersection
        return area_union


def intersection(ai, bi):
    if len(ai) == 4:
        w = min(ai[2], bi[2]) - max(ai[0], bi[0])
        h = min(ai[3], bi[3]) - max(ai[1], bi[1])
        if w < 0 or h < 0:
            return 0
        return w * h
    else:
        w = min(ai[3], bi[3]) - max(ai[0], bi[0])
        h = min(ai[4], bi[4]) - max(ai[1], bi[1])
        d = min(ai[5], bi[5]) - max(ai[2], bi[2])
        if w < 0 or h < 0 or d < 0:
            return 0
        return w * h * d


def iou(a, b):
    if len(a) == 4:
        # a and b should be (x1,y1,x2,y2)
        if a[0] >= a[2] or a[1] >= a[3] or b[0] >= b[2] or b[1] >= b[3]:
            return 0.0
        area_i = intersection(a, b)
        area_u = union(a, b, area_i)
        return float(area_i) / float(area_u + 1e-6)
    else:
        if a[0] >= a[3] or a[1] >= a[4] or a[2] >= a[5] or b[0] >= b[3] or b[1] >= b[4] or b[2] >= b[5]:
            return 0.0
        area_i = intersection(a, b)
        area_u = union(a, b, area_i)
        return float(area_i) / float(area_u + 1e-6)

def get_new_img_size3d(width, height, depth, img_min_side=600):
    min_size = min(width, height, depth)
    resized_height = int(float(img_min_side) * height / min_size)
    resized_width = int(float(img_min_side) * width / min_size)
    resized_depth = int(float(img_min_side) * depth / min_size)
    return resized_width, resized_height, resized_depth


def get_new_img_size(width, height, img_min_side=600):
    # if depth==None:
    #     if width <= height:
    #         resized_height = int(float(img_min_side) * height / width)
    #         resized_width = img_min_side
    #     else:
    #         resized_width = int(float(img_min_side) * width / height)
    #         resized_height = img_min_side
    #     return resized_width, resized_height
    # else:
    min_size = min(width, height)
    resized_height = int(float(img_min_side) * height / min_size)
    resized_width = int(float(img_min_side) * width / min_size)
    return resized_width, resized_height

class SampleSelector:
    def __init__(self, class_count):
        # ignore classes that have zero samples
        self.classes = [b for b in class_count.keys() if class_count[b] > 0]
        self.class_cycle = itertools.cycle(self.classes)
        self.curr_class = next(self.class_cycle)

    def skip_sample_for_balanced_class(self, img_data):

        class_in_img = False

        for bbox in img_data['bboxes']:

            cls_name = bbox['class']

            if cls_name == self.curr_class:
                class_in_img = True
                self.curr_class = next(self.class_cycle)
                break

        if class_in_img:
            return False
        else:
            return True


def calc_rpn3d(C, img_data, width, height, depth, resized_width, resized_height, resized_depth,
               img_length_calc_function):
    downscale = float(C.rpn_stride)
    anchor_sizes = C.anchor_box_scales
    anchor_ratios = C.anchor_box_ratios
    num_anchors = len(anchor_sizes) * len(anchor_ratios)
    n_anchratios = len(anchor_ratios)

    # calculate the output map size based on the network architecture
    (output_width, output_height, output_depth) = img_length_calc_function(resized_width, resized_height, resized_depth)

    # initialise empty output objectives
    y_rpn_overlap = np.zeros((output_height, output_width, output_depth, num_anchors))
    y_is_box_valid = np.zeros((output_height, output_width, output_depth, num_anchors))
    y_rpn_regr = np.zeros((output_height, output_width, output_depth, num_anchors * 6))

    num_bboxes = len(img_data['bboxes'])
    num_anchors_for_bbox = np.zeros(num_bboxes).astype(int)
    best_anchor_for_bbox = -1 * np.ones((num_bboxes, 6)).astype(int)
    best_iou_for_bbox = np.zeros(num_bboxes).astype(np.float32)
    best_x_for_bbox = np.zeros((num_bboxes, 6)).astype(int)
    best_dx_for_bbox = np.zeros((num_bboxes, 6)).astype(np.float32)

    # get the GT box coordinates, and resize to account for image resizing
    gta = np.zeros((num_bboxes, 6))
    for bbox_num, bbox in enumerate(img_data['bboxes']):
        # get the GT box coordinates, and resize to account for image resizing
        gta[bbox_num, 0] = bbox['x1'] * (resized_width / float(width))
        gta[bbox_num, 1] = bbox['x2'] * (resized_width / float(width))
        gta[bbox_num, 2] = bbox['y1'] * (resized_height / float(height))
        gta[bbox_num, 3] = bbox['y2'] * (resized_height / float(height))
        gta[bbox_num, 4] = bbox['z1'] * (resized_depth / float(depth))
        gta[bbox_num, 5] = bbox['z2'] * (resized_depth / float(depth))

    # rpn ground truth
    for anchor_size_idx in range(len(anchor_sizes)):
        for anchor_ratio_idx in range(n_anchratios):
            anchor_x = anchor_sizes[anchor_size_idx] * anchor_ratios[anchor_ratio_idx][0]
            anchor_y = anchor_sizes[anchor_size_idx] * anchor_ratios[anchor_ratio_idx][1]
            anchor_z = anchor_sizes[anchor_size_idx] * anchor_ratios[anchor_ratio_idx][2]

            for ix in range(output_width):
                # x-coordinates of the current anchor box
                x1_anc = downscale * (ix + 0.5) - anchor_x / 2
                x2_anc = downscale * (ix + 0.5) + anchor_x / 2

                # ignore boxes that go across image boundaries
                if x1_anc < 0 or x2_anc > resized_width:
                    continue

                for jy in range(output_height):

                    # y-coordinates of the current anchor box
                    y1_anc = downscale * (jy + 0.5) - anchor_y / 2
                    y2_anc = downscale * (jy + 0.5) + anchor_y / 2

                    # ignore boxes that go across image boundaries
                    if y1_anc < 0 or y2_anc > resized_height:
                        continue

                    for kz in range(output_depth):
                        # bbox_type indicates whether an anchor should be a target
                        bbox_type = 'neg'

                        z1_anc = downscale * (kz + 0.5) - anchor_z / 2
                        z2_anc = downscale * (kz + 0.5) + anchor_z / 2
                        if z1_anc < 0 or z2_anc > resized_depth:
                            continue

                        # this is the best IOU for the (x,y) coord and the current anchor
                        # note that this is different from the best IOU for a GT bbox
                        best_iou_for_loc = 0.0

                        for bbox_num in range(num_bboxes):

                            # get IOU of the current GT box and the current anchor box
                            curr_iou = iou([gta[bbox_num, 0], gta[bbox_num, 3], gta[bbox_num, 1],
                                            gta[bbox_num, 4], gta[bbox_num, 2], gta[bbox_num, 5]],
                                           [x1_anc, y1_anc, z1_anc,
                                            x2_anc, y2_anc, z2_anc])
                            # calculate the regression targets if they will be needed
                            if curr_iou > best_iou_for_bbox[bbox_num] or curr_iou > C.rpn_max_overlap:
                                cx = (gta[bbox_num, 0] + gta[bbox_num, 1]) / 2.0
                                cy = (gta[bbox_num, 2] + gta[bbox_num, 3]) / 2.0
                                cz = (gta[bbox_num, 4] + gta[bbox_num, 5]) / 2.0
                                cxa = (x1_anc + x2_anc) / 2.0
                                cya = (y1_anc + y2_anc) / 2.0
                                cza = (z1_anc + z2_anc) / 2.0

                                tx = (cx - cxa) / (x2_anc - x1_anc)
                                ty = (cy - cya) / (y2_anc - y1_anc)
                                tz = (cz - cza) / (z2_anc - z1_anc)
                                tw = np.log((gta[bbox_num, 1] - gta[bbox_num, 0]) / (x2_anc - x1_anc))
                                th = np.log((gta[bbox_num, 3] - gta[bbox_num, 2]) / (y2_anc - y1_anc))
                                td = np.log((gta[bbox_num, 5] - gta[bbox_num, 3]) / (z2_anc - z1_anc))

                            if img_data['bboxes'][bbox_num]['class'] != 'bg':
                                # all GT boxes should be mapped to an anchor box, so we keep track of which anchor box was best
                                if curr_iou > best_iou_for_bbox[bbox_num]:
                                    best_anchor_for_bbox[bbox_num] = [jy, ix, kz, anchor_ratio_idx, anchor_size_idx]
                                    best_iou_for_bbox[bbox_num] = curr_iou
                                    best_x_for_bbox[bbox_num, :] = [x1_anc, x2_anc, y1_anc, y2_anc, z1_anc, z2_anc]
                                    best_dx_for_bbox[bbox_num, :] = [tx, ty, tw, th, tz, td]

                                # we set the anchor to positive if the IOU is >0.7 (it does not matter if there was another better box, it just indicates overlap)
                                if curr_iou > C.rpn_max_overlap:
                                    bbox_type = 'pos'
                                    num_anchors_for_bbox[bbox_num] += 1
                                    # we update the regression layer target if this IOU is the best for the current (x,y) and anchor position
                                    if curr_iou > best_iou_for_loc:
                                        best_iou_for_loc = curr_iou
                                        best_regr = (tx, ty, tw, th, tz, td)

                                # if the IOU is >0.3 and <0.7, it is ambiguous and no included in the objective
                                if C.rpn_min_overlap < curr_iou < C.rpn_max_overlap:
                                    # gray zone between neg and pos
                                    if bbox_type != 'pos':
                                        bbox_type = 'neutral'

                        # turn on or off outputs depending on IOUs
                        if bbox_type == 'neg':
                            y_is_box_valid[jy, ix, kz, anchor_ratio_idx + n_anchratios * anchor_size_idx] = 1
                            y_rpn_overlap[jy, ix, kz, anchor_ratio_idx + n_anchratios * anchor_size_idx] = 0
                        elif bbox_type == 'neutral':
                            y_is_box_valid[jy, ix, kz, anchor_ratio_idx + n_anchratios * anchor_size_idx] = 0
                            y_rpn_overlap[jy, ix, kz, anchor_ratio_idx + n_anchratios * anchor_size_idx] = 0
                        elif bbox_type == 'pos':
                            y_is_box_valid[jy, ix, kz, anchor_ratio_idx + n_anchratios * anchor_size_idx] = 1
                            y_rpn_overlap[jy, ix, kz, anchor_ratio_idx + n_anchratios * anchor_size_idx] = 1
                            start = 6 * (anchor_ratio_idx + n_anchratios * anchor_size_idx)
                            y_rpn_regr[jy, ix, kz, start:start + 6] = best_regr

    # we ensure that every bbox has at least one positive RPN region

    for idx in range(num_anchors_for_bbox.shape[0]):
        if num_anchors_for_bbox[idx] == 0:
            # no box with an IOU greater than zero ...
            if best_anchor_for_bbox[idx, 0] == -1:
                continue
            y_is_box_valid[
                best_anchor_for_bbox[idx, 0],
                best_anchor_for_bbox[idx, 1],
                best_anchor_for_bbox[idx, 2],
                best_anchor_for_bbox[idx, 3] + n_anchratios * best_anchor_for_bbox[idx, 4]
            ] = 1
            y_rpn_overlap[
                best_anchor_for_bbox[idx, 0],
                best_anchor_for_bbox[idx, 1],
                best_anchor_for_bbox[idx, 2],
                best_anchor_for_bbox[idx, 3] + n_anchratios * best_anchor_for_bbox[idx, 4]
            ] = 1
            start = 4 * (best_anchor_for_bbox[idx, 3] + n_anchratios * best_anchor_for_bbox[idx, 4])
            y_rpn_regr[
            best_anchor_for_bbox[idx, 0],
            best_anchor_for_bbox[idx, 1],
            best_anchor_for_bbox[idx, 2],
            start:start + 4
            ] = best_dx_for_bbox[idx, :]

    y_rpn_overlap = np.transpose(y_rpn_overlap, (3, 0, 1, 2))
    y_rpn_overlap = np.expand_dims(y_rpn_overlap, axis=0)

    y_is_box_valid = np.transpose(y_is_box_valid, (3, 0, 1, 2))
    y_is_box_valid = np.expand_dims(y_is_box_valid, axis=0)

    y_rpn_regr = np.transpose(y_rpn_regr, (3, 0, 1, 2))
    y_rpn_regr = np.expand_dims(y_rpn_regr, axis=0)

    pos_locs = np.where(np.logical_and(y_rpn_overlap[0, :, :, :, :] == 1, y_is_box_valid[0, :, :, :, :] == 1))
    neg_locs = np.where(np.logical_and(y_rpn_overlap[0, :, :, :, :] == 0, y_is_box_valid[0, :, :, :, :] == 1))

    num_pos = len(pos_locs[0])

    # one issue is that the RPN has many more negative than positive regions, so we turn off some of the negative
    # regions. We also limit it to 256 regions.
    num_regions = 256

    if len(pos_locs[0]) > num_regions / 2:
        val_locs = random.sample(range(len(pos_locs[0])), len(pos_locs[0]) - num_regions / 2)
        y_is_box_valid[
            0, pos_locs[0][val_locs], pos_locs[1][val_locs], pos_locs[2][val_locs], pos_locs[3][val_locs]] = 0
        num_pos = num_regions / 2

    if len(neg_locs[0]) + num_pos > num_regions:
        val_locs = random.sample(range(len(neg_locs[0])), len(neg_locs[0]) - num_pos)
        y_is_box_valid[
            0, neg_locs[0][val_locs], neg_locs[1][val_locs], neg_locs[2][val_locs], pos_locs[3][val_locs]] = 0

    y_rpn_cls = np.concatenate([y_is_box_valid, y_rpn_overlap], axis=1)
    y_rpn_regr = np.concatenate([np.repeat(y_rpn_overlap, 6, axis=1), y_rpn_regr], axis=1)

    return np.copy(y_rpn_cls), np.copy(y_rpn_regr)


def calc_rpn(C, img_data, width, height, resized_width, resized_height, img_length_calc_function):
    downscale = float(C.rpn_stride)
    anchor_sizes = C.anchor_box_scales
    anchor_ratios = C.anchor_box_ratios
    num_anchors = len(anchor_sizes) * len(anchor_ratios)
    n_anchratios = len(anchor_ratios)

    # calculate the output map size based on the network architecture
    (output_width, output_height) = img_length_calc_function(resized_width, resized_height)

    # initialise empty output objectives
    y_rpn_overlap = np.zeros((output_height, output_width, num_anchors))
    y_is_box_valid = np.zeros((output_height, output_width, num_anchors))
    y_rpn_regr = np.zeros((output_height, output_width, num_anchors * 4))

    num_bboxes = len(img_data['bboxes'])
    num_anchors_for_bbox = np.zeros(num_bboxes).astype(int)
    best_anchor_for_bbox = -1 * np.ones((num_bboxes, 4)).astype(int)
    best_iou_for_bbox = np.zeros(num_bboxes).astype(np.float32)
    best_x_for_bbox = np.zeros((num_bboxes, 4)).astype(int)
    best_dx_for_bbox = np.zeros((num_bboxes, 4)).astype(np.float32)

    # get the GT box coordinates, and resize to account for image resizing
    gta = np.zeros((num_bboxes, 4))
    for bbox_num, bbox in enumerate(img_data['bboxes']):
        # get the GT box coordinates, and resize to account for image resizing
        gta[bbox_num, 0] = bbox['x1'] * (resized_width / float(width))
        gta[bbox_num, 1] = bbox['x2'] * (resized_width / float(width))
        gta[bbox_num, 2] = bbox['y1'] * (resized_height / float(height))
        gta[bbox_num, 3] = bbox['y2'] * (resized_height / float(height))

    # rpn ground truth

    for anchor_size_idx in range(len(anchor_sizes)):
        for anchor_ratio_idx in range(n_anchratios):
            anchor_x = anchor_sizes[anchor_size_idx] * anchor_ratios[anchor_ratio_idx][0]
            anchor_y = anchor_sizes[anchor_size_idx] * anchor_ratios[anchor_ratio_idx][1]

            for ix in range(output_width):
                # x-coordinates of the current anchor box
                x1_anc = downscale * (ix + 0.5) - anchor_x / 2
                x2_anc = downscale * (ix + 0.5) + anchor_x / 2

                # ignore boxes that go across image boundaries
                if x1_anc < 0 or x2_anc > resized_width:
                    continue

                for jy in range(output_height):

                    # y-coordinates of the current anchor box
                    y1_anc = downscale * (jy + 0.5) - anchor_y / 2
                    y2_anc = downscale * (jy + 0.5) + anchor_y / 2

                    # ignore boxes that go across image boundaries
                    if y1_anc < 0 or y2_anc > resized_height:
                        continue

                    # bbox_type indicates whether an anchor should be a target
                    bbox_type = 'neg'

                    # this is the best IOU for the (x,y) coord and the current anchor
                    # note that this is different from the best IOU for a GT bbox
                    best_iou_for_loc = 0.0

                    for bbox_num in range(num_bboxes):

                        # get IOU of the current GT box and the current anchor box
                        curr_iou = iou([gta[bbox_num, 0], gta[bbox_num, 2], gta[bbox_num, 1], gta[bbox_num, 3]],
                                       [x1_anc, y1_anc, x2_anc, y2_anc])
                        # calculate the regression targets if they will be needed
                        if curr_iou > best_iou_for_bbox[bbox_num] or curr_iou > C.rpn_max_overlap:
                            cx = (gta[bbox_num, 0] + gta[bbox_num, 1]) / 2.0
                            cy = (gta[bbox_num, 2] + gta[bbox_num, 3]) / 2.0
                            cxa = (x1_anc + x2_anc) / 2.0
                            cya = (y1_anc + y2_anc) / 2.0

                            tx = (cx - cxa) / (x2_anc - x1_anc)
                            ty = (cy - cya) / (y2_anc - y1_anc)
                            tw = np.log((gta[bbox_num, 1] - gta[bbox_num, 0]) / (x2_anc - x1_anc))
                            th = np.log((gta[bbox_num, 3] - gta[bbox_num, 2]) / (y2_anc - y1_anc))

                        if img_data['bboxes'][bbox_num]['class'] != 'bg':
                            # all GT boxes should be mapped to an anchor box, so we keep track of which anchor box was best
                            if curr_iou > best_iou_for_bbox[bbox_num]:
                                best_anchor_for_bbox[bbox_num] = [jy, ix, anchor_ratio_idx, anchor_size_idx]
                                best_iou_for_bbox[bbox_num] = curr_iou
                                best_x_for_bbox[bbox_num, :] = [x1_anc, x2_anc, y1_anc, y2_anc]
                                best_dx_for_bbox[bbox_num, :] = [tx, ty, tw, th]

                            # we set the anchor to positive if the IOU is >0.7 (it does not matter if there was another better box, it just indicates overlap)
                            if curr_iou > C.rpn_max_overlap:
                                bbox_type = 'pos'
                                num_anchors_for_bbox[bbox_num] += 1
                                # we update the regression layer target if this IOU is the best for the current (x,y) and anchor position
                                if curr_iou > best_iou_for_loc:
                                    best_iou_for_loc = curr_iou
                                    best_regr = (tx, ty, tw, th)

                            # if the IOU is >0.3 and <0.7, it is ambiguous and no included in the objective
                            if C.rpn_min_overlap < curr_iou < C.rpn_max_overlap:
                                # gray zone between neg and pos
                                if bbox_type != 'pos':
                                    bbox_type = 'neutral'

                    # turn on or off outputs depending on IOUs
                    if bbox_type == 'neg':
                        y_is_box_valid[jy, ix, anchor_ratio_idx + n_anchratios * anchor_size_idx] = 1
                        y_rpn_overlap[jy, ix, anchor_ratio_idx + n_anchratios * anchor_size_idx] = 0
                    elif bbox_type == 'neutral':
                        y_is_box_valid[jy, ix, anchor_ratio_idx + n_anchratios * anchor_size_idx] = 0
                        y_rpn_overlap[jy, ix, anchor_ratio_idx + n_anchratios * anchor_size_idx] = 0
                    elif bbox_type == 'pos':
                        y_is_box_valid[jy, ix, anchor_ratio_idx + n_anchratios * anchor_size_idx] = 1
                        y_rpn_overlap[jy, ix, anchor_ratio_idx + n_anchratios * anchor_size_idx] = 1
                        start = 4 * (anchor_ratio_idx + n_anchratios * anchor_size_idx)
                        y_rpn_regr[jy, ix, start:start + 4] = best_regr

    # we ensure that every bbox has at least one positive RPN region

    for idx in range(num_anchors_for_bbox.shape[0]):
        if num_anchors_for_bbox[idx] == 0:
            # no box with an IOU greater than zero ...
            if best_anchor_for_bbox[idx, 0] == -1:
                continue
            y_is_box_valid[
                best_anchor_for_bbox[idx, 0],
                best_anchor_for_bbox[idx, 1],
                best_anchor_for_bbox[idx, 2] + n_anchratios * best_anchor_for_bbox[idx, 3]
            ] = 1
            y_rpn_overlap[
                best_anchor_for_bbox[idx, 0],
                best_anchor_for_bbox[idx, 1],
                best_anchor_for_bbox[idx, 2] + n_anchratios * best_anchor_for_bbox[idx, 3]
            ] = 1
            start = 4 * (best_anchor_for_bbox[idx, 2] + n_anchratios * best_anchor_for_bbox[idx, 3])
            y_rpn_regr[
            best_anchor_for_bbox[idx, 0],
            best_anchor_for_bbox[idx, 1],
            start:start + 4
            ] = best_dx_for_bbox[idx, :]

    y_rpn_overlap = np.transpose(y_rpn_overlap, (2, 0, 1))
    y_rpn_overlap = np.expand_dims(y_rpn_overlap, axis=0)

    y_is_box_valid = np.transpose(y_is_box_valid, (2, 0, 1))
    y_is_box_valid = np.expand_dims(y_is_box_valid, axis=0)

    y_rpn_regr = np.transpose(y_rpn_regr, (2, 0, 1))
    y_rpn_regr = np.expand_dims(y_rpn_regr, axis=0)

    pos_locs = np.where(np.logical_and(y_rpn_overlap[0, :, :, :] == 1, y_is_box_valid[0, :, :, :] == 1))
    neg_locs = np.where(np.logical_and(y_rpn_overlap[0, :, :, :] == 0, y_is_box_valid[0, :, :, :] == 1))

    num_pos = len(pos_locs[0])

    # one issue is that the RPN has many more negative than positive regions, so we turn off some of the negative
    # regions. We also limit it to 256 regions.
    num_regions = 256

    if len(pos_locs[0]) > num_regions / 2:
        val_locs = random.sample(range(len(pos_locs[0])), len(pos_locs[0]) - num_regions / 2)
        y_is_box_valid[0, pos_locs[0][val_locs], pos_locs[1][val_locs], pos_locs[2][val_locs]] = 0
        num_pos = num_regions / 2

    if len(neg_locs[0]) + num_pos > num_regions:
        val_locs = random.sample(range(len(neg_locs[0])), len(neg_locs[0]) - num_pos)
        y_is_box_valid[0, neg_locs[0][val_locs], neg_locs[1][val_locs], neg_locs[2][val_locs]] = 0

    y_rpn_cls = np.concatenate([y_is_box_valid, y_rpn_overlap], axis=1)
    y_rpn_regr = np.concatenate([np.repeat(y_rpn_overlap, 4, axis=1), y_rpn_regr], axis=1)

    return np.copy(y_rpn_cls), np.copy(y_rpn_regr)


class threadsafe_iter:
    """Takes an iterator/generator and makes it thread-safe by
    serializing call to the `next` method of given iterator/generator.
    """

    def __init__(self, it):
        self.it = it
        self.lock = threading.Lock()

    def __iter__(self):
        return self

    def next(self):
        with self.lock:
            return next(self.it)


def threadsafe_generator(f):
    """A decorator that takes a generator function and makes it thread-safe.
    """

    def g(*a, **kw):
        return threadsafe_iter(f(*a, **kw))

    return g


def get_anchor_gt(all_img_data, class_count, C, img_length_calc_function, backend, mode='train'):
    # The following line is not useful with Python 3.5, it is kept for the legacy
    # all_img_data = sorted(all_img_data)

    sample_selector = SampleSelector(class_count)

    while True:
        if mode == 'train':
            np.random.shuffle(all_img_data)

        for img_data in all_img_data:
            try:
                if C.use3d == False:
                    if C.balanced_classes and sample_selector.skip_sample_for_balanced_class(img_data):
                        continue

                    # read in image, and optionally add augmentation
                    if mode == 'train':
                        img_data_aug, x_img = augment(img_data, C, augment=True)
                    else:
                        img_data_aug, x_img = augment(img_data, C, augment=False)

                    (width, height) = (img_data_aug['width'], img_data_aug['height'])
                    (rows, cols, _) = x_img.shape

                    assert cols == width
                    assert rows == height

                    # get image dimensions for resizing
                    (resized_width, resized_height) = get_new_img_size(width, height)
                    # resize the image so that smallest side is length = 600px
                    x_img = cv2.resize(x_img, (resized_width, resized_height), interpolation=cv2.INTER_CUBIC)
                    try:
                        y_rpn_cls, y_rpn_regr = calc_rpn(C, img_data_aug, width, height, resized_width, resized_height,
                                                         img_length_calc_function)
                    except:
                        continue

                    # Zero-center by mean pixel, and preprocess image
                    x_img = x_img[:, :, (2, 1, 0)]  # BGR -> RGB
                    x_img = x_img.astype(np.float32)
                    x_img[:, :, 0] -= C.img_channel_mean[0]
                    x_img[:, :, 1] -= C.img_channel_mean[1]
                    x_img[:, :, 2] -= C.img_channel_mean[2]
                    x_img /= C.img_scaling_factor

                    x_img = np.transpose(x_img, (2, 0, 1))
                    x_img = np.expand_dims(x_img, axis=0)

                    y_rpn_regr[:, y_rpn_regr.shape[1] // 2:, :, :] *= C.std_scaling

                    if backend == 'tf':
                        x_img = np.transpose(x_img, (0, 2, 3, 1))
                        y_rpn_cls = np.transpose(y_rpn_cls, (0, 2, 3, 1))
                        y_rpn_regr = np.transpose(y_rpn_regr, (0, 2, 3, 1))
                    yield np.copy(x_img), [np.copy(y_rpn_cls), np.copy(y_rpn_regr)], img_data_aug
                else:
                    if C.balanced_classes and sample_selector.skip_sample_for_balanced_class(img_data):
                        continue

                    # read in image, and optionally add augmentation
                    if mode == 'train':
                        img_data_aug, x_img = augment(img_data, C, augment=False)
                    else:
                        img_data_aug, x_img = augment(img_data, C, augment=False)

                    (width, height, depth) = (img_data_aug['width'], img_data_aug['height'], img_data_aug['depth'])
                    (rows, cols, zs, _) = x_img.shape

                    assert cols == width
                    assert rows == height
                    assert zs == depth

                    # get image dimensions for resizing
                    (resized_width, resized_height, resized_depth) = get_new_img_size3d(width, height, depth)
                    # resize the image so that smallest side is length = 600px
                    x_img = cv2.resize(x_img, (resized_width, resized_height, resized_depth),
                                       interpolation=cv2.INTER_CUBIC)
                    try:
                        y_rpn_cls, y_rpn_regr = calc_rpn3d(C, img_data_aug, width, height, depth,
                                                           resized_width, resized_height, resized_depth,
                                                           img_length_calc_function)
                    except:
                        continue

                    # Zero-center by mean pixel, and preprocess image
                    # x_img = x_img[:, :, (2, 1, 0)]  # BGR -> RGB
                    x_img = x_img.astype(np.float32)
                    # x_img[:, :, 0] -= C.img_channel_mean[0]
                    # x_img[:, :, 1] -= C.img_channel_mean[1]
                    # x_img[:, :, 2] -= C.img_channel_mean[2]
                    # x_img /= C.img_scaling_factor

                    x_img = np.transpose(x_img, (3, 0, 1, 2))
                    x_img = np.expand_dims(x_img, axis=0)

                    # y_rpn_regr[:, y_rpn_regr.shape[1] // 2:, :, :] *= C.std_scaling

                    if backend == 'tf':
                        x_img = np.transpose(x_img, (0, 2, 3, 4, 1))
                        y_rpn_cls = np.transpose(y_rpn_cls, (0, 2, 3, 4, 1))
                        y_rpn_regr = np.transpose(y_rpn_regr, (0, 2, 3, 4, 1))

                    yield np.copy(x_img), [np.copy(y_rpn_cls), np.copy(y_rpn_regr)], img_data_aug

            except Exception as e:
                print(e)
                continue
