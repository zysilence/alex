#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np

from multiprocessing import *

import __init__

from SDS.ml.gmm import GMM

#from SDS.components.vad import GMMVAD
from SDS.utils.htk import *

max_files = 100
n_iter = 10
n_mixies = 128 # 64 # 32 # 16


train_data_sil = 'data_vad_sil/data/*.wav'
train_data_sil_aligned = 'data_vad_sil/vad-silence.mlf'

mlf_sil = MLF(train_data_sil_aligned, max_files = max_files)
mlf_sil.filter_zero_segments()
# map all sp, _noise_, _laugh_, _inhale_ to sil
mlf_sil.sub('sp', 'sil')
mlf_sil.sub('_noise_', 'sil')
mlf_sil.sub('_laugh_', 'sil')
mlf_sil.sub('_inhale_', 'sil')
# map everything except of sil to speech
mlf_sil.sub('sil', 'speech', False)
mlf_sil.merge()
#mlf_sil.times_to_seconds()
mlf_sil.times_to_frames()
mlf_sil.trim_segments(3)

print "The length of sil segments in sil:    ", mlf_sil.count_length('sil')
print "The length of speech segments in sil: ", mlf_sil.count_length('speech')

train_data_speech = 'data_voip_en/train/*.wav'
train_data_speech_aligned = 'asr_model_voip_en/aligned_best.mlf'

mlf_speech = MLF(train_data_speech_aligned, max_files = max_files)
mlf_speech.filter_zero_segments()
# map all sp, _noise_, _laugh_, _inhale_ to sil
mlf_speech.sub('sp', 'sil')
mlf_speech.sub('_noise_', 'sil')
mlf_speech.sub('_laugh_', 'sil')
mlf_speech.sub('_inhale_', 'sil')
# map everything except of sil to speech
mlf_speech.sub('sil', 'speech', False)
mlf_speech.merge()
#mlf_speech.times_to_seconds()
mlf_speech.times_to_frames()
mlf_speech.trim_segments(3)

print "The length of sil segments in speech:    ", mlf_speech.count_length('sil')
print "The length of speech segments in speech: ", mlf_speech.count_length('speech')

def train_speech_gmm():
  vta_speech = MLFMFCCOnlineAlignedArray(filter='speech', usec0 = False)
  vta_speech.append_mlf(mlf_sil)
  vta_speech.append_trn(train_data_sil)
  vta_speech.append_mlf(mlf_speech)
  vta_speech.append_trn(train_data_speech)

  data_speech = list(vta_speech)
  #data_speech = vta_speech

  gmm_speech = GMM(n_features = 36, n_components = 1, n_iter = n_iter)
  gmm_speech.fit(data_speech)
  for i in range(n_mixies):
    if i > 64:
      gmm_sil.mixup(8)
    elif i > 32:
      gmm_sil.mixup(6)
    elif i > 16:
      gmm_sil.mixup(4)
    elif i > 8:
      gmm_sil.mixup(2)
    else:
      gmm_sil.mixup(1)

    gmm_speech.fit(data_speech)
    print "Speech weights:"
    print gmm_speech.weights
    print "Speech LP:", gmm_speech.log_probs[-1]
    print "-"*120
  gmm_speech.save_model('model_voip_en/vad_speech_sds_mfcc.gmm')
  return

def train_sil_gmm():
  vta_sil = MLFMFCCOnlineAlignedArray(filter='sil', usec0 = False)
  vta_sil.append_mlf(mlf_sil)
  vta_sil.append_trn(train_data_sil)
  vta_sil.append_mlf(mlf_speech)
  vta_sil.append_trn(train_data_speech)

  data_sil = list(vta_sil)
#  data_sil = vta_sil

  gmm_sil = GMM(n_features = 36, n_components = 1, n_iter = n_iter)
  gmm_sil.fit(data_sil)
  for i in range(n_mixies):
    if i > 64:
      gmm_sil.mixup(8)
    elif i > 32:
      gmm_sil.mixup(6)
    elif i > 16:
      gmm_sil.mixup(4)
    elif i > 8:
      gmm_sil.mixup(2)
    else:
      gmm_sil.mixup(1)

    gmm_sil.fit(data_sil)
    print "Sil weights:"
    print gmm_sil.weights
    print "Sil LP:", gmm_sil.log_probs[-1]
    print "-"*120
  gmm_sil.save_model('model_voip_en/vad_sil_sds_mfcc.gmm')

p_speech = Process(target=train_speech_gmm)
p_sil = Process(target=train_sil_gmm)
p_speech.start()
p_sil.start()

p_sil.join()
print "Sil GMM training finished"
p_speech.join()
print "Speech GMM training finished"

#train_speech_gmm()
#train_sil_gmm()


print '-'*120
print 'VAD GMM test'
print '-'*120
gmm_speech = GMM(n_features = 0)
gmm_speech.load_model('model_voip_en/vad_speech_sds_mfcc.gmm')
gmm_sil = GMM(n_features = 0)
gmm_sil.load_model('model_voip_en/vad_sil_sds_mfcc.gmm')

vta = MLFMFCCOnlineAlignedArray()
vta.append_mlf(mlf_speech)
vta.append_trn(train_data_speech)

accuracy = 0.0
n = 0
for frame, label in vta:
  log_prob_speech = gmm_speech.score(frame)
  log_prob_sil = gmm_sil.score(frame)

  ratio = log_prob_speech - log_prob_sil
  if ratio >= 0:
    rec_label = 'speech'
  else:
    rec_label = 'sil'

  if rec_label == label:
    accuracy += 1.0

  n += 1

accuracy = accuracy*100.0/n

print "VAD accuracy : %0.3f%% " % accuracy
