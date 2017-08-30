import argparse
import numpy as np
from load_data import *
from sputils import *
import torch
from torch.autograd import Variable
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader

from models import *

from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import confusion_matrix, accuracy_score

parser = argparse.ArgumentParser(description='PyTorch Language ID Classifier Trainer')
parser.add_argument('--num-classes', type=int, default=None, metavar='b',
                    help='number of classes')
parser.add_argument('--batch-size', type=int, default=8, metavar='b',
                    help='batch size')
parser.add_argument('--freq-bands', type=int, default=224,
                    help='number of frequency bands to use')
parser.add_argument('--window-size', type=int, default=2048,
                    help='size of window for stft')
parser.add_argument('--languages', type=str, nargs='+', default=None,
                    help='languages to filter by')
parser.add_argument('--seed', type=int, default=1111,
                    help='random seed')
parser.add_argument('--cuda', action='store_true',
                    help='use CUDA')
parser.add_argument('--validate', action='store_true',
                    help='do out-of-bag validation')
parser.add_argument('--use-chromagrams', action='store_true',
                    help='use chromagrams')
parser.add_argument('--log-interval', type=int, default=4,
                    help='reports per epoch')
parser.add_argument('--file-list', type=str, default="data/trainingset.csv",
                    help='csv file with audio files and labels')
parser.add_argument('--grams-path', type=str, default=None,
                    help='path to load spectro/chroma -grams')
parser.add_argument('--model', type=str, default="cnn",
                    help='choose model type')
parser.add_argument('--model-path', type=str, default=None,
                    help='path to model parameters')
parser.add_argument('--load-model', action='store_true',
                    help='load model from disk')
parser.add_argument('--save-model', action='store_true',
                    help='path to save the final model')
args = parser.parse_args()

def transform(tensor, model = "cnn"):
    if model == "cnn":
        return(Variable(tensor.unsqueeze(1)))
    elif model == "resnet":
        return(Variable(torch.stack([tensor, tensor, tensor], dim=1)))

# set seed
torch.manual_seed(args.seed)

# load spectro/chroma -grams
gtype = "chromagrams" if args.use_chromagrams else "spectrograms"
inputs, labels = get_grams(use_chromagrams = args.use_chromagrams, N = None,
                           grams_path = args.grams_path, languages = args.languages,
                           window_size = args.window_size, freq_bands = args.freq_bands,
                           filelist = args.file_list)
inputs = inputs[:,:,:427]
print(inputs.shape)

# encode labels
le = LabelEncoder()
le.fit(spconfig.lang_classes)
num_targets = le.classes_.shape[0]
labels_encoded = le.transform(labels)
print(le.classes_)

# Create Network
if args.model == "cnn":
    nn_builder = cnn.Net
    nnargs = {}
elif args.model == "resnet":
    nn_builder = resnet.resnetX
    nnargs = {}
else:
    print("unknown model type")
net = nn_builder(num_classes=num_targets, **nnargs)
model_save_path = "output/states/"+args.model+"_model_"+gtype+".pt"
if args.model_path is None:
    net.load_state_dict(torch.load(model_save_path))
else:
    net.load_state_dict(torch.load(args.model_path))
net.eval()
print(net)

# make predictions in batches
output = []
inputs = torch.from_numpy(inputs).float()
labels_encoded = torch.from_numpy(labels_encoded[:inputs.size(0)])
print(labels_encoded.size())

trainset = TensorDataset(inputs, labels_encoded)
trainloader = DataLoader(trainset, batch_size=args.batch_size, shuffle=False)

for i, (minibatch, l) in enumerate(trainloader):
    output += [net(transform(minibatch, args.model)).data]
output = torch.cat(output)
#output_numpy = nn.functional.softmax(Variable(output)).data.numpy()
#np.set_printoptions(formatter={'float': lambda x: "{0:0.2f}".format(x)})
#print(output_numpy)
print(output.max(1)[1].numpy().ravel())
yhat = le.inverse_transform(output.max(1)[1].numpy().ravel())
#print([(act, pred) for act, pred in zip(labels, yhat)])
y_t  = le.inverse_transform(labels_encoded.numpy().ravel())
print(confusion_matrix(y_t, yhat))