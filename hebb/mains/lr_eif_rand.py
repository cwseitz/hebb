import numpy as np
import matplotlib.pyplot as plt
import hebb_backend
import json
from hebb.models import *

##################################################
## Predicting spike train cross-correlations as
## for excitatory-inhibitory random network
## using the linear response approximation
##################################################
## Author: Clayton Seitz
## Copyright: 2021, The Hebb Project
## Email: cwseitz@uchicago.edu
##################################################

save_dir = '/home/cwseitz/Desktop/data/'

#######################################
## Load the parameters used
#######################################

with open(save_dir + 'params.json', 'r') as fh:
    params = json.load(fh)

N = params['N']
N_e = params['N_e']
N_i = params['N_i']
gl = params['gl'][0]
Cm = params['Cm'][0]
DeltaT = params['DeltaT'][0]
vT = params['vT'][0]
vth = params['vth'][0]
vlb = params['vlb'][0]
vre = params['vre'][0]
vl = params['vl'][0]
tref = params['tref'][0]
dV = 0.1
V = np.arange(vlb, vth, dV)

#as far as in know, these dont matter
tau_x = 200
Vx = -85
gx = 0
Dx = 8
Vxh = -40
xi = 1/(1+np.exp(-(V-Vxh)/Dx))

mu0 = params['mxe']
var = params['vxe']
D = gl*np.sqrt(2*var*Cm/gl)

taud = 0*np.ones((N,1)) #synaptic delay
tausyne = params['tausyne']
tausyni = params['tausyni']
taus = np.zeros((N,1))
taus[:N_e] = tausyne
taus[N_e:] = tausyni

Tmax = 50 #Maximum time lag over which to calculate cross-correlations (ms)
dt = 1 #Bin size for which to calculate cross-correlations (ms)
u1 = 1
df = 1/2/Tmax
fmax = 1/2/dt
freq = np.arange(-fmax, fmax, df)
idx = np.argwhere(np.abs(freq) < 1e-6)
freq[idx] = 1e-6
freq = freq.tolist()
nfreq = len(freq)

xi = [x.item() for x in xi]
params = [N,gl,Cm,DeltaT,vT,vl,vth,vlb,dV,vre,tref,tau_x,Vx,gx,mu0,var,xi]

#Generate the connectivity matrix
net = np.load(save_dir + 'mc_eif_rand_weights.npz')['arr_0']

##################################################
## Fixed point iteration to find the rates
##################################################

tup = hebb_backend.fp_eif(params)
P0,p0,J0,x0,r0 = tup

num_rate_fp_its = 20
rates = r0*np.ones((N,))

for i in range(num_rate_fp_its):
    tmp_rates = []
    for j in range(N):
        s = np.sum(net[j,:]*rates)
        mu = mu0 + s
        params = [N,gl,Cm,DeltaT,vT,vl,vth,vlb,dV,vre,tref,tau_x,Vx,gx,mu,var,xi]
        tup = hebb_backend.fp_eif(params)
        tmp_rates.append(tup[4])
    rates = np.array(tmp_rates)


####################################################################
## Find linear response and synaptic kernel in the frequency domain
####################################################################

At = np.zeros((N,nfreq),dtype=np.cdouble)
Ft = np.zeros((N,nfreq),dtype=np.cdouble)
Ct0 = np.zeros((N,nfreq))

tup = hebb_backend.fp_eif(params)
P0,p0,J0,x0,r0 = tup

for i in range(N):

    print(f'Neuron {i}')
    mu_in = mu0 + np.sum(net[i,:]*rates)
    params = [N,gl,Cm,DeltaT,vT,vl,vth,vlb,dV,vre,tref,tau_x,Vx,gx,x0,mu_in,var,u1,r0,P0,xi,p0,freq,nfreq]

    V1r,V1i,x1r,x1i,Ar,Ai = hebb_backend.lr_eif(params)
    params = [N,gl,Cm,DeltaT,vT,vl,vth,vlb,dV,vre,tref,tau_x,Vx,gx,x0,mu_in,var,u1,r0,freq,nfreq]
    f0r,f0i = hebb_backend.fpt_eif(params)

    f0 = np.array(f0r) + np.array(f0i)*1j
    C0 = r0*(1+2*np.real(f0/(1-f0)))

    Ft[i,:] = np.exp(1j*-2*np.pi*np.array(freq)*taud[i])/(1+1j*2*np.pi*np.array(freq)*taus[i])
    At[i,:] = np.array(Ar) + np.array(Ai)*1j
    Ct0[i,:] = C0

plt.imshow(np.real(At))
plt.show()

# Ft_e_r = np.mean(np.real(At[:N_e]),axis=0)
# Ft_e_i = np.mean(np.imag(At[:N_e]),axis=0)
# plt.plot(Ft_e_r)
# plt.plot(Ft_e_i)
# plt.show()
