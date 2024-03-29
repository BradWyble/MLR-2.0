from label_network import load_checkpoint_colorlabels, load_checkpoint_shapelabels, s_classes, vae_shape_labels
import torch
from mVAE import vae, load_checkpoint, image_activations, activations
from torch.utils.data import DataLoader, ConcatDataset
from dataset_builder import dataset_builder
import matplotlib.pyplot as plt
from joblib import dump, load
from torchvision import utils
import torch.nn.functional as F
import os
from sklearn.metrics import accuracy_score

v = '_v1' # which model version to use, set to '' for the most recent
load_checkpoint(f'output_emnist_recurr{v}/checkpoint_300.pth') # load VAE
load_checkpoint_shapelabels(f'output_label_net{v}/checkpoint_shapelabels5.pth') # load shape label net
clf_shapeS = load(f'classifier_output{v}/ss.joblib')

vals = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']

vae.eval()

output_folder_path = 'letter_sim_output' # the output folder for the generated simulations

if not os.path.exists(output_folder_path):
    os.mkdir(output_folder_path)

def letter_sim(char_1, char_2, l_1, l_2, noise = 1, save_img = False):
    # char_1, char_2: type: integer, which digit or letters to combine together, corresponds to the index of the desired character in the vals list
    # l_1, l_2: type: integer, the location of the first and second character respectively
    # noise: type: float, scales the noise added into the latent representations
    # save_img: type: boolean, whether to save the generated images to the output folder
    with torch.no_grad():
        # build one hot vectors to be passed to the label networks
        num_labels = F.one_hot(torch.tensor([char_1, char_2]).cuda(), num_classes=s_classes).float().cuda() # shape labels for input chars
        loc_labels = torch.zeros((2,100)).cuda()
        loc_labels[0][l_1], loc_labels[1][l_2] = 1, 1 # set locations for char1 and 2

        # generate shape latents from the labels, the noise param scales the added normal dist in the sampling call
        z_shape_labels = vae_shape_labels(num_labels, noise)

        # location latent from the location vector
        z_location = vae.location_encoder(loc_labels)

        # pass latents through decoder
        recon_retinal = vae.decoder_retinal(z_shape_labels, 0, z_location, None, 'shape')
        # clamp shape recons to form one image of the combined numbers
        img1 = recon_retinal[0,:,:,(l_1+6):34]
        img2 = recon_retinal[1,:,:,(l_1+6):34]
        comb_img = torch.clamp(img1 + img2, 0, 0.5) * 1.5
        comb_img = comb_img.view(1,3,28,28)

        l1_junk, l2_junk, z_shape, z_color, z_location = activations(comb_img)

        pred_ss = clf_shapeS.predict(z_shape.cpu())
        out_pred = pred_ss[0].item() # predicted character

        recon_shape = vae.decoder_shape(z_shape, 0, 0)

        if save_img == True:
            utils.save_image(comb_img, f'{output_folder_path}/{char_1}_{char_2}_sim.png')
            utils.save_image(recon_shape, f'{output_folder_path}/{char_1}_{char_2}_sim_recon.png')
            utils.save_image(img1, f'{output_folder_path}/{char_1}.png')
            utils.save_image(img2, f'{output_folder_path}/{char_2}.png')
        
    return out_pred # returns integer index of predicted character in the vals list

# demo:
# generates a 1 and a 3 at positions 0 and 7 respectively, a moderate amount of noise is added to the latent representations and the generated image is saved
pred = letter_sim(char_1 = 1, char_2 = 3, l_1 = 0, l_2 = 7, noise = 140, save_img = True)
print(vals[pred])
# accuracy can be calculated using:
# true_list = [correct_char] * len(prediction_list)
# accuracy = accuracy_score(true_list, prediction_list)

# Valerie: