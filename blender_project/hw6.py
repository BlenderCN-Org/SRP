import numpy as np
import math
import random
from sklearn.svm import SVC

def prox_op_l1(x):
    return np.sign(x) * np.maximum(0, np.fabs(x) - 1)

#proximal operator for 1/2 * |x|^2
def prox_op_l2squared(y):
    alpha = 0.001
    return y / (1 + alpha)

def hinge_loss_gradient(y, x, w):
    return np.zeros(len(w)) if y * x.dot(w) >= 1 else -y * x

def dataset_error(X, Y, w):
    count = 0
    for i in range(0, len(Y)):
        if Y[i] * X[i].dot(w) >= 1:
            count = count + 1
    return 1 - (float(count) / len(Y))

def SVM_l1(X, Y, w, C_1, num_iters):
    gamma = 0.5
    for i in range(0, num_iters):
        k = random.randint(0, len(Y) - 1)
        w = prox_op_l1(w - gamma * C_1 * hinge_loss_gradient(Y[k], X[k], w))
    return w

def SVM_l2(X, Y, w, C_2, num_iters):
    gamma = 0.3
    for i in range(0, num_iters):
        k = random.randint(0, len(Y) - 1)
        w = prox_op_l2squared(w - gamma * C_2 * hinge_loss_gradient(Y[k], X[k], w))
    return w

print ('Reading data files...')
X_train = np.loadtxt('train.data', dtype=float)
Y_train = np.loadtxt('train.labels', dtype=int)
X_test = np.loadtxt('test.data', dtype=float)
Y_test = np.loadtxt('test.labels', dtype=int)

clf = SVC()
clf.fit(X_train, Y_train) 
Y_pred = clf.predict(X_test)
count = 0
for i in range(0, len(Y)):
    if Y_pred[i] * Y_test[i] >= 1:
        count = count + 1        
print('test error = ', + str(1 - (float(count) / len(Y))))

#print ('Training L1 SVM...')
#w1 = SVM_l1(X_train, Y_train, np.zeros(len(X_train[0])), 1, 300000)
#print ('Training L2 SVM...')
#w2 = SVM_l2(X_train, Y_train, np.random.randint(-10, 10, len(X_train[0])), 1, 300000)
#print ('Test error for L1 SVM weights: ' + str(dataset_error(X_test, Y_test, w1)))
#print ('Test error for L2 SVM weights: ' + str(dataset_error(X_test, Y_test, w2)))
