import ffield
import genericmatrix
import math


class RSCode:
    def __init__(self, n, k, log2FieldSize=-1, shouldUseLUT=-1):
        if (log2FieldSize < 0):
            log2FieldSize = int(math.ceil(math.log(n * k) / math.log(2)))
        self.field = ffield.FField(log2FieldSize, useLUT=shouldUseLUT)
        self.n = n
        self.k = k
        self.fieldSize = 1 << log2FieldSize
        # finite filed size should be equal to or larger than n*k
        assert(n*k <= self.fieldSize)
        self.create_encoder_matrix()
        self.encoderMatrix.Transpose()
        self.encoderMatrix.LowerGaussianElim()
        self.encoderMatrix.UpperInverse()
        self.encoderMatrix.Transpose()

    def __repr__(self):
        rep = ('<RSCode (n,k) = (' + `self.n` + ', ' + `self.k` + ')'
               + '  over GF(2^' + `self.field.n` + ')\n'
               + `self.encoderMatrix` + '\n' + '>')
        return rep

    def create_encoder_matrix(self):
        self.encoderMatrix = genericmatrix.GenericMatrix(
            (self.n, self.k), 0, 1, self.field.Add, self.field.Subtract,
            self.field.Multiply, self.field.Divide)
        # for i in range(self.k):
        #     self.encoderMatrix[i, i] = 1
        # for i in range(self.k):
        #     self.encoderMatrix[self.k, i] = 1
        #     self.encoderMatrix[self.k + 1, i] = int(math.pow(2, self.k - 1 - i))
        self.encoderMatrix[0,0] = 1
        for i in range(0,self.n):
            term = 1
            for j in range(0, self.k):
                self.encoderMatrix[i,j] = term
                term = self.field.Multiply(term,i+1)

    def encode(self, data):
        assert len(data) == self.k, 'Encode: input data must be size k list.'
        return self.encoderMatrix.LeftMulColumnVec(data)

    def prepare_decoder(self, unErasedLocations):
        if len(unErasedLocations) != self.k:
            raise ValueError, 'input must be exactly length k'

        limitedEncoder = genericmatrix.GenericMatrix(
            (self.k, self.k), 0, 1, self.field.Add, self.field.Subtract,
            self.field.Multiply, self.field.Divide)
        for i in range(0, self.k):
            limitedEncoder.SetRow(
                i, self.encoderMatrix.GetRow(unErasedLocations[i]))
        self.decoderMatrix = limitedEncoder.Inverse()

    def decode(self, unErasedTerms):
        return self.decoderMatrix.LeftMulColumnVec(unErasedTerms)

    def decode_immediate(self, data):
        if len(data) != self.n:
            raise ValueError, 'input must be a length n list'

        unErasedLocations = []
        unErasedTerms = []
        for i in range(self.n):
            if None != data[i]:
                unErasedLocations.append(i)
                unErasedTerms.append(data[i])
        self.prepare_decoder(unErasedLocations[0:self.k])
        return self.decode(unErasedTerms[0:self.k])
