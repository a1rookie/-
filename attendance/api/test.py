
# from numpy import dot, zeros
# from numpy import mat
# from numpy.linalg import inv

# 创建矩阵(1行3列)
# x = mat([1, 2, 3])
# 创建矩阵(3行3列)
# y = mat([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
# 创建零矩阵(3行3列)
# z = mat(zeros((3, 3), dtype=int))
# print("x:\n", x)
# print("y:\n", y)
# print("z:\n", z)
# 矩阵的乘法运算(matmul)
# print("x*y:\n", np.matmul(x, y))
# print("x*y:\n", x * y)
# 矩阵的点乘运算(dot)，在二维矩阵中点乘结果和matmul一致
# print("x*y:\n", dot(x, y))
import numpy as np
x = np.ones(shape=(3, 3), dtype=float)
print(x)
