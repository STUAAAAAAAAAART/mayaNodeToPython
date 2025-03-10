melString = [
	'\tsetAttr ".ws[0]" -type "nurbsCurve" ', # toss
	'\t\t3 6 0 no 3', # index 0
	'\t\t11 0 0 0 1 2 3 4 5 6 6 6', # pop 0th and hold, append rest as list element 
	'\t\t9', #append normally
	'\t\t-2.0000000000001679 5 13.00000000000019', # append each as triples
	'\t\t-3.5393162393164861 5 9.4111111111112198',
	'\t\t-6.6179487179490444 5 2.2333333333332837',
	'\t\t4.4717948717950335 5 -3.9333333333333247',
	'\t\t12.730769230769258 5 -4.5000000000000782',
	'\t\t-1.3948717948718699 5 9.93333333333333',
	'\t\t10.848717948718051 5 18.76666666666673',
	'\t\t11.616239316239362 5 9.5888888888889348',
	'\t\t11.999999999999996 5 5',
	'\t\t;' # toss
	]

melString.pop() # don't need the last bit
melString.pop(0) # don't need the MEL command
for i in range(len(melString)):
	melString[i] = melString[i].replace("\t",'')


melString[0] = melString[0].split(' ')

for i in range(len(melString[0])):
	try:
		melString[0][i] = int(melString[0][i])
	except:
		if melString[0][i] == "yes":
			melString[0][i] = True
		elif melString[0][i] == "no":
			melString[0][i] = False
		else:
			raise ValueError("problems parsing info string into int and bool")
melString[1] = melString[1].split(' ')
melStringKnotCount = int(melString[1].pop(0)) # remove knot count
for i in range(len(melString[1])):
	melString[1][i] = int(melString[1][i])
	# raise default error if this can't be parsed

buildList = []

buildList += melString[0] # basic info
buildList.append(melString[1]) # knot data [0,0,0,1,1,1,2,2,2...]
buildList += [int(melString[2]), melStringKnotCount] # number of knots, number of CVs

melStringCvs = melString[3:]

for cv in range(len(melStringCvs)):
	# triples now
	melStringCvs[cv] = melStringCvs[cv].split(' ')
	for i in range(len(melStringCvs[cv])):
		melStringCvs[cv][i] = float(melStringCvs[cv][i])
		# raise default error if this can't be parsed
buildList += melStringCvs

for i in buildList:
	print(i)