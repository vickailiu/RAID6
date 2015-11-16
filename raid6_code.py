import ffield
import genericmatrix


class RSCode:
    def __init__(self, n, k, log2_field_size=8):
        self.field = ffield.FField(log2_field_size, useLUT=-1)
        self.n = n
        self.k = k
        self.encoder_matrix = genericmatrix.GenericMatrix((n, k), 0, 1,
                                                          self.field.Add, self.field.Subtract,
                                                          self.field.Multiply, self.field.Divide)
        self.encoder_matrix[0, 0] = 1
        for i in range(0, n):
            term = 1
            for j in range(0, k):
                self.encoder_matrix[i, j] = term
                term = self.field.Multiply(term, i+1)
        self.encoder_matrix.Transpose()
        self.encoder_matrix.LowerGaussianElim()
        self.encoder_matrix.UpperInverse()
        self.encoder_matrix.Transpose()
        self.decoder_matrix = None

    def encode(self, data):
        assert len(data) == self.k, 'Encode: input data must be size k list.'
        return self.encoder_matrix.LeftMulColumnVec(data)

    def prepare_decoder(self, unerased_locations):
        if len(unerased_locations) != self.k:
            raise ValueError('input must be exactly length k')

        limited_encoder = genericmatrix.GenericMatrix((self.k, self.k), 0, 1,
                                                      self.field.Add, self.field.Subtract,
                                                      self.field.Multiply, self.field.Divide)
        for i in range(0, self.k):
            limited_encoder.SetRow(i, self.encoder_matrix.GetRow(unerased_locations[i]))
        self.decoder_matrix = limited_encoder.Inverse()

    def decode(self, unerased_terms):
        return self.decoder_matrix.LeftMulColumnVec(unerased_terms)
