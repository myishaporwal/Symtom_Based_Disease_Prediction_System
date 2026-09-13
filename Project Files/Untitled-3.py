def sumtwo(array,target):
    for i in range (len(array)):
        if (array[i]+array[i+1])==target:
            return (array[i],array[i+1])
x=[2,7,11,15]
t1=9
print(sumtwo(x,t1))