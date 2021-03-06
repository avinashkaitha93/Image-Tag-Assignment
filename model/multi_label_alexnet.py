

import numpy as np
import tensorflow as tf
from datetime import datetime
from alexnet import AlexNet
from generator import Generator
import read_data as readData
import evaluation as eval
from sklearn import utils
from tqdm import *


import logging
logging.getLogger().setLevel(logging.INFO)

learning_rates = [0.000001]
num_epochs = 10
batch_size = 450
path = 'data/dataset/'

print "####################### Multi-label AlexNet #####################"
print "loading the dataset: please wait for a while!"
X1_train,X2_train,Y_train = readData.read(path+'train/')
X1_val,X2_val,Y_val = readData.read(path+'validate/')
X1_test,X2_test,Y_test = readData.read(path+'test/')

    

X_train_generator = Generator(X1_train,X2_train,Y_train)
X_validate_generator = Generator(X1_val,X2_val,Y_val)
X_test_generator = Generator(X1_test,X2_test,Y_test)

train_batches_per_epoch = np.floor(X_train_generator.num_samples / batch_size).astype(np.int16)
val_batches_per_epoch = np.floor(X_validate_generator.num_samples / batch_size).astype(np.int16)
test_batches_per_epoch = np.floor(X_test_generator.num_samples / batch_size).astype(np.int16)

num_classes = Y_train.shape[1]
dropout_rate = 0.5

skip_layers = ['fc8']
train_layers = ['dense3']


for learning_rate in learning_rates:
    
    tf.reset_default_graph()

    x1 = tf.placeholder(tf.float32, [batch_size, 227, 227, 3])
    y = tf.placeholder(tf.float32, [None, num_classes])
    keep_prob = tf.placeholder(tf.float32)
    
    # Initialize model
    model = AlexNet(x1, keep_prob, skip_layers)
    
    alexnet_output = model.dropout7
    
    score = tf.layers.dense(inputs=alexnet_output, units=num_classes, activation=tf.nn.sigmoid, name = 'dense3')
    
    # List of trainable variables of the layers we want to train
    var_list = [v for v in tf.trainable_variables() if v.name.split('/')[0] in train_layers]
    
    # Op for calculating the loss
    with tf.name_scope("cross_ent"):
        #loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits = score, labels = y))  
        loss = -tf.reduce_sum( (  (y*tf.log(score + 1e-9)) + ((1-y) * tf.log(1 - score + 1e-9)) )  , name='xentropy' )
        #loss = tf.reduce_sum(tf.abs(tf.nn.sigmoid_cross_entropy_with_logits(labels=y, logits=score)))
      
    # Train op
    with tf.name_scope("train"):
        # Get gradients of all trainable variables
        gradients = tf.gradients(loss, var_list)
        gradients = list(zip(gradients, var_list))
      
        # Create optimizer and apply gradient descent to the trainable variables
        optimizer = tf.train.MomentumOptimizer(learning_rate,0.9) #RMSPropOptimizer
        train_op = optimizer.apply_gradients(grads_and_vars=gradients)
    
    # Evaluation op: Accuracy of the model
    with tf.name_scope("accuracy"):
        #correct_pred = tf.equal(tf.argmax(score, 1), tf.argmax(y, 1))
        #accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))
        accuracy = loss#tf.reduce_sum(tf.abs(tf.subtract(y,score)))
    
    
    accu = np.zeros(4)
    prec = np.zeros(4)
    rec = np.zeros(4)
    batches = 0
    
    X_test_generator.reset()
    
    with tf.Session() as sess:
        # Initialize all variables
        sess.run(tf.global_variables_initializer())
        #sess.run(tf.local_variables_initializer())
      
        # Load the pretrained weights into the non-trainable layer
        model.load_initial_weights(sess)
      
    
        #print("{} Start training...".format(datetime.now()))
        
        # Loop over number of epochs
        
        
        X1_train,X2_train,Y_train = utils.shuffle(X1_train,X2_train,Y_train)
        X1_val,X2_val,Y_val,X1_test,X2_test,Y_test = utils.shuffle(X1_val,X2_val,Y_val,X1_test,X2_test,Y_test)
        X_train_generator.shuffle(X1_train,X2_train,Y_train)
        X_validate_generator.shuffle(X1_val,X2_val,Y_val)
        
        for epoch in range(num_epochs):
            
            X_train_generator.reset()
            X_validate_generator.reset()
            
            print("{} Epoch number: {}".format(datetime.now(), epoch+1)), " Training:"
            
            step = 1
            
            for i in tqdm(range(train_batches_per_epoch)):
            #while step < train_batches_per_epoch:
                
                # Get a batch of images and labels
                batch_xs1, batch_xs2, batch_ys = X_train_generator.next_batch(batch_size)
                
                # And run the training op
                sess.run(train_op, feed_dict={x1: batch_xs1,
                                              y: batch_ys, 
                                              keep_prob: dropout_rate})
                
                pass    
                #step += 1
                
            # Validate the model on the entire validation set
            print("{} Start validation:".format(datetime.now()))
            test_acc = 0.
            test_count = 0
            for _ in range(val_batches_per_epoch):
                batch_tx1, batch_tx2, batch_ty = X_validate_generator.next_batch(batch_size)
                acc = sess.run(loss, feed_dict={x1: batch_tx1, 
                                                    y: batch_ty, 
                                                    keep_prob: 1.})
                test_acc += acc
                test_count += 1
                
            test_acc /= test_count
            print 'Validation loss = %.6f' %(test_acc)
        
        
            #print("{} Start test:".format(datetime.now()))
            test_acc = 0.
            test_count = 0
            
        for _ in range(test_batches_per_epoch):
            
            batch_tx1, batch_tx2, batch_ty = X_test_generator.next_batch(batch_size)
            acc,predictions = sess.run([loss,score], feed_dict={x1: batch_tx1, 
                                                y: batch_ty, 
                                                keep_prob: 1.})
            test_acc += acc
            test_count += 1
                            
            
            a, p, r = eval.evaluate(batch_ty,predictions,k=1)
            accu[0] += a
            prec[0] += p
            rec[0] += r
            
            a, p, r = eval.evaluate(batch_ty,predictions,k=3)
            accu[1] += a
            prec[1] += p
            rec[1] += r
            
            a, p, r = eval.evaluate(batch_ty,predictions,k=5)
            accu[2] += a
            prec[2] += p
            rec[2] += r
            
            a, p, r = eval.evaluate(batch_ty,predictions,k=10)
            accu[3] += a
            prec[3] += p
            rec[3] += r
            
            
            batches += 1
        test_acc /= test_count
        print 'Test loss = %.6f' %(test_acc)
    
    
    
    accu /= (1. * test_batches_per_epoch * batch_size)
    prec /= (1. * test_batches_per_epoch * batch_size)
    rec /= (1. * test_batches_per_epoch * batch_size)
    
    print 'learning rate: %.9f' %(learning_rate)
    print 'K:1, acc: %.6f, prec: %.6f, rec: %.6f' %(accu[0], prec[0], rec[0])
    print 'K:3, acc: %.6f, prec: %.6f, rec: %.6f' %(accu[1], prec[1], rec[1])
    print 'K:5, acc: %.6f, prec: %.6f, rec: %.6f' %(accu[2], prec[2], rec[2])
    print 'K:10, acc: %.6f, prec: %.6f, rec: %.6f' %(accu[3], prec[3], rec[3])
    
    file = open('output/multi_label_alexnet.txt', 'w')
    file.write('K:1, acc: %.6f, prec: %.6f, rec: %.6f' %(accu[0], prec[0], rec[0]))
    file.write("\n")
    file.write('K:3, acc: %.6f, prec: %.6f, rec: %.6f' %(accu[1], prec[1], rec[1]))
    file.write("\n")
    file.write('K:5, acc: %.6f, prec: %.6f, rec: %.6f' %(accu[2], prec[2], rec[2]))
    file.write("\n")
    file.write('K:10, acc: %.6f, prec: %.6f, rec: %.6f' %(accu[3], prec[3], rec[3]))
    file.close()
    

