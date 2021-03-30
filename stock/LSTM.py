#coding=gbk
'''
Created on 2017��2��20��

@author: Lu.yipiao
'''
import pandas as pd
import numpy as np
import pymysql

import matplotlib.pyplot as plt
import tensorflow as tf

#���峣��
rnn_unit=10       #hidden layer units
input_size=7
output_size=1
lr=0.0006         #ѧϰ��
#�������������������������������������������ݡ�������������������������������������������
data_dir='./dataset/'
# stockname='dataset_2'
stockname='601318'
checkpoint_dir='./model/'+stockname+'/'


def openfile(filename):
    f=open(data_dir+filename+'.csv',encoding='gb2312')
    df=pd.read_csv(f, index_col='����', parse_dates=True).sort_index()   #�����Ʊ����
    df = df.drop(df[df.���̼�==0].index)
    # df=pd.read_csv(f)
    # print(df)
    data=df.iloc[:,2:11].values
    return data

data=openfile(stockname)
# print(data)

dbip = '127.0.0.1'  # ���ݿ�IP��ַ
suname = 'root'  # �û���
supwd = 'root'  # ����
dbname = 'stockweb'  # ���ݿ���
chars = 'utf8'  # �����ʽ

#��ȡѵ����
def get_train_data(batch_size=60,time_step=20,train_begin=0,train_end=2400):
    batch_index=[]
    data_train=data[train_begin:train_end]
    normalized_train_data=(data_train-np.mean(data_train,axis=0))/np.std(data_train,axis=0)  #��׼��
    train_x,train_y=[],[]   #ѵ����
    print(train_x,train_y)
    for i in range(len(normalized_train_data)-time_step):
       if i % batch_size==0:
           batch_index.append(i)
       x=normalized_train_data[i:i+time_step,:7]
       y=normalized_train_data[i:i+time_step,7,np.newaxis]
       train_x.append(x.tolist())
       train_y.append(y.tolist())
    batch_index.append((len(normalized_train_data)-time_step))
    return batch_index,train_x,train_y



#��ȡ���Լ�
def get_test_data(time_step=20,test_begin=2459):
    data_test=data[test_begin:]
    mean=np.mean(data_test,axis=0)
    std=np.std(data_test,axis=0)
    normalized_test_data=(data_test-mean)/std  #��׼��
    size=(len(normalized_test_data)+time_step-1)//time_step  #��size��sample
    test_x,test_y=[],[]
    for i in range(size-1):
       x=normalized_test_data[i*time_step:(i+1)*time_step,:7]
       y=normalized_test_data[i*time_step:(i+1)*time_step,7]
       test_x.append(x.tolist())
       test_y.extend(y)
    test_x.append((normalized_test_data[(i+1)*time_step:,:7]).tolist())
    test_y.extend((normalized_test_data[(i+1)*time_step:,7]).tolist())
    return mean,std,test_x,test_y



#�������������������������������������������������������������������������������������
#����㡢�����Ȩ�ء�ƫ��

weights={
         'in':tf.Variable(tf.random.normal([input_size,rnn_unit])),
         'out':tf.Variable(tf.random.normal([rnn_unit,1]))
        }
biases={
        'in':tf.Variable(tf.constant(0.1,shape=[rnn_unit,])),
        'out':tf.Variable(tf.constant(0.1,shape=[1,]))
       }

#�������������������������������������������������������������������������������������
def lstm(X):
    batch_size=tf.shape(X)[0]
    time_step=tf.shape(X)[1]
    w_in=weights['in']
    b_in=biases['in']
    input=tf.reshape(X,[-1,input_size])  #��Ҫ��tensorת��2ά���м��㣬�����Ľ����Ϊ���ز������
    input_rnn=tf.matmul(input,w_in)+b_in
    input_rnn=tf.reshape(input_rnn,[-1,time_step,rnn_unit])  #��tensorת��3ά����Ϊlstm cell������
    cell=tf.nn.rnn_cell.BasicLSTMCell(rnn_unit)
    init_state=cell.zero_state(batch_size,dtype=tf.float32)
    output_rnn,final_states=tf.nn.dynamic_rnn(cell, input_rnn,initial_state=init_state, dtype=tf.float32)  #output_rnn�Ǽ�¼lstmÿ������ڵ�Ľ����final_states�����һ��cell�Ľ��
    output=tf.reshape(output_rnn,[-1,rnn_unit]) #��Ϊ����������
    w_out=weights['out']
    b_out=biases['out']
    pred=tf.matmul(output,w_out)+b_out
    return pred,final_states



#������������������������������������ѵ��ģ�͡�����������������������������������
def train_lstm(batch_size=80,time_step=15,train_begin=100,train_end=2600):
    X=tf.compat.v1.placeholder(tf.float32, shape=[None,time_step,input_size])
    Y=tf.compat.v1.placeholder(tf.float32, shape=[None,time_step,output_size])
    batch_index,train_x,train_y=get_train_data(batch_size,time_step,train_begin,train_end)
    pred,_=lstm(X)
    #��ʧ����
    loss=tf.reduce_mean(tf.square(tf.reshape(pred,[-1])-tf.reshape(Y, [-1])))
    train_op=tf.train.AdamOptimizer(lr).minimize(loss)
    saver=tf.train.Saver(tf.global_variables(),max_to_keep=15)
    module_file = tf.train.latest_checkpoint(checkpoint_dir)
    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())
        # saver.restore(sess, module_file)
        #�ظ�ѵ��1000��
        for i in range(1000):
            for step in range(len(batch_index)-1):
                _,loss_=sess.run([train_op,loss],feed_dict={X:train_x[batch_index[step]:batch_index[step+1]],Y:train_y[batch_index[step]:batch_index[step+1]]})
            print(i,loss_)
            if i % 200==0:
                print("����ģ�ͣ�",saver.save(sess,checkpoint_dir+stockname,global_step=i))





#��������������������������������Ԥ��ģ�͡���������������������������������������
def prediction(time_step=20):
    X=tf.compat.v1.placeholder(tf.float32, shape=[None,time_step,input_size])
    #Y=tf.compat.v1.placeholder(tf.float32, shape=[None,time_step,output_size])
    mean,std,test_x,test_y=get_test_data(time_step)
    pred,_=lstm(X)
    saver=tf.train.Saver(tf.global_variables())
    with tf.compat.v1.Session() as sess:
        #�����ָ�
        module_file = tf.train.latest_checkpoint(checkpoint_dir)
        saver.restore(sess, module_file)
        test_predict=[]
        for step in range(len(test_x)-1):
          prob=sess.run(pred,feed_dict={X:[test_x[step]]})
          predict=prob.reshape((-1))
          test_predict.extend(predict)
        test_y=np.array(test_y)*std[7]+mean[7]
        test_predict=np.array(test_predict)*std[7]+mean[7]
        acc=np.average(np.abs(test_predict-test_y[:len(test_predict)])/test_y[:len(test_predict)])  #ƫ��
        # ������ͼ��ʾ���
        conn = pymysql.connect(
            host=dbip,
            user=suname, password=supwd,
            db=dbname,
            charset=chars)
        cursor = conn.cursor()
        sql = "insert into prediction(stockcode,predic) values('%s','%s')"%(stockname,test_predict)
        print(sql)
        cursor.execute(sql)
        conn.commit()
        plt.figure()
        plt.plot(list(range(len(test_predict))), test_predict, color='b')
        plt.plot(list(range(len(test_y))), test_y,  color='r')
        plt.show()



# train_lstm()
# prediction()

# with tf.variable_scope('train'):
#     train_lstm()
# with tf.variable_scope('train',reuse=True):
#     prediction()