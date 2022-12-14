import tkinter as tk

from dahuffman import HuffmanCodec
from skimage import measure

from encoding.rle_modular import rle_modular
from gui.Decompress import Decompression
from jpeg.decompression import *
from jpeg.dictionary_util import *
from util.bilinear_trasformation import bilinear_interpolation
from util.dictionary_util_modular import compress_dict_modular

sys.setrecursionlimit(9999)


class RleAndEntropy:

    def __init__(self, root, img1, img2, img3, out, filename):
        self.filename = filename
        self.root = root
        self.image1 = img1
        self.image2 = img2
        self.image3 = img3
        self.out = out
        self.list_out = self.out.split(';')
        self.has_dct = self.list_out[2] != '0'
        self.block_size = 16 if self.list_out[2] == '6' else int(self.list_out[2])

        self.entropy = None

        self.img_height, self.img_width = self.list_out[0].split('x')
        self.color_space = 'RBG' if self.list_out[1] == 'R' else ('YCbCr444' if self.list_out[1] == '4' else 'YCbCr420')
        self.dct = 'Has DCT' if self.has_dct else 'Does not have DCT'
        self.quant = self.list_out[3] != 'N'
        self.quant_val = 0 if (not self.quant or self.list_out[3] == 'T') else int(self.list_out[3])
        self.predictive = self.list_out[4] != 'N'
        self.vertical = self.list_out[4] == 'V'

        self.calc_entropy()

        print("------RLE ENTROPY-----")
        print(self.out)

        # canvas
        self.height = 900
        self.width = 1500
        self.canvas = tk.Canvas(self.root, height=self.height, width=self.width, bg="#263D42")

        # info frame
        self.frame = tk.Frame(self.canvas, bg="#354552")
        self.frame.place(relheight=0.72, relwidth=0.6, relx=0.025, rely=0.15)

        # labels
        self.img_height = "Height: " + self.img_height
        self.label1 = tk.Label(self.frame, text=self.img_height, justify=tk.CENTER,
                               width=80, height=1, font=("Roboto", 22, "bold"), bg="#354552", fg="white")
        self.label1.pack(side=tk.TOP, pady=20)

        self.img_width = "Width: " + self.img_width
        self.label2 = tk.Label(self.frame, text=self.img_width, justify=tk.CENTER,
                               width=80, height=1, font=("Roboto", 22, "bold"), bg="#354552", fg="white")
        self.label2.pack(side=tk.TOP, pady=20)

        self.color_space = "Color space: " + self.color_space
        self.label3 = tk.Label(self.frame, text=self.color_space, justify=tk.CENTER,
                               width=80, height=1, font=("Roboto", 22, "bold"), bg="#354552", fg="white")
        self.label3.pack(side=tk.TOP, pady=20)

        self.dct = "DCT: " + self.dct
        self.label4 = tk.Label(self.frame, text=self.dct, justify=tk.CENTER,
                               width=80, height=1, font=("Roboto", 22, "bold"), bg="#354552", fg="white")
        self.label4.pack(side=tk.TOP, pady=20)

        if self.has_dct:
            self.dct = "DCT: " + self.dct
            self.label5 = tk.Label(self.frame, text='Block size: ' + str(self.block_size) + 'x' + str(self.block_size),
                                   justify=tk.CENTER,
                                   width=80, height=1, font=("Roboto", 22, "bold"), bg="#354552", fg="white")
            self.label5.pack(side=tk.TOP, pady=20)

        self.label6 = tk.Label(self.frame, text='Quantization: ' + str(self.quant), justify=tk.CENTER,
                               width=80, height=1, font=("Roboto", 22, "bold"), bg="#354552", fg="white")
        self.label6.pack(side=tk.TOP, pady=20)

        if self.quant_val != 0:
            self.label7 = tk.Label(self.frame, text='Quantization value: ' + str(self.quant_val), justify=tk.CENTER,
                                   width=80, height=1, font=("Roboto", 22, "bold"), bg="#354552", fg="white")
            self.label7.pack(side=tk.TOP, pady=20)

        pred = 'No' if not self.predictive else 'Yes' if self.dct else 'Vertical' if self.vertical else 'Horizontal'
        self.label8 = tk.Label(self.frame, text='Predictive encoding: ' + pred, justify=tk.CENTER,
                               width=80, height=1, font=("Roboto", 22, "bold"), bg="#354552", fg="white")
        self.label8.pack(side=tk.TOP, pady=20)

        self.label9 = tk.Label(self.frame, text='Entropy: ' + str(self.entropy), justify=tk.CENTER,
                               width=80, height=1, font=("Roboto", 22, "bold"), bg="#354552", fg="white")
        self.label9.pack(side=tk.TOP, pady=20)

        # drop-down frame
        self.button_frame = tk.Frame(self.canvas, bg="#354552")
        self.button_frame.place(relwidth=0.325, relheight=0.3, relx=0.65, rely=0.3)

        # drop down menu
        self.options1 = ["Entropy", "RLE and Entropy"]
        self.clicked1 = tk.StringVar()
        self.clicked1.set("RLE and Entropy")

        self.drop = tk.OptionMenu(self.button_frame, self.clicked1, *self.options1)
        self.drop.config(width=40, font=("Roboto", 18, "bold"), foreground="#FFFFFF", background="#263D42")
        self.drop.pack(side=tk.TOP, pady=10)

        button_dropdown = tk.Button(self.button_frame, text="Choose", height=5, width=25, fg="white", bg="#263D42")
        button_dropdown.configure(command=self.accept_encoding)
        button_dropdown.pack(side=tk.BOTTOM, pady=10)

        self.canvas.pack()

    def calc_entropy(self):
        image = np.zeros((self.image1.shape[0], self.image1.shape[1], 3))

        image[:, :, 0] = self.image1
        image[:, :, 1] = self.image2 if '420' not in self.color_space else bilinear_interpolation(self.image2, 2)[
                                                                           :self.image1.shape[0], :self.image1.shape[1]]
        image[:, :, 2] = self.image3 if '420' not in self.color_space else bilinear_interpolation(self.image3, 2)[
                                                                           :self.image1.shape[0], :self.image1.shape[1]]

        self.entropy = measure.shannon_entropy(image)
        print("entropy5:", self.entropy)

    def accept_encoding(self):
        if self.clicked1.get() in self.options1:
            rle = "RLE" in self.clicked1.get()
            entropy = "Entropy" in self.clicked1.get()

            if rle:
                q = 5
                if self.has_dct:
                    zigzag_arr_1 = blockify(self.image1, self.block_size)
                    zigzag_arr_2 = blockify(self.image2, self.block_size)
                    zigzag_arr_3 = blockify(self.image3, self.block_size)

                    rle1 = rle_modular(zigzag_arr_1)
                    rle1 += rle_modular(zigzag_arr_2)
                    rle1 += rle_modular(zigzag_arr_3)

                    # TODO: make it faster
                    huff_dict, coded_arr = find_huffman_dict_and_array(rle1)

                    self.out += 'R;'

                    img_bin = string_to_ascii(self.out) + huff_dict + coded_arr

                    self.canvas.destroy()
                    Decompression(self.root, img_bin, self.out, self.filename)

                else:
                    arr1 = flatten_image(self.image1, not self.vertical)
                    arr2 = flatten_image(self.image2, not self.vertical)
                    arr3 = flatten_image(self.image3, not self.vertical)

                    rle1 = rle_modular(arr1, False)
                    rle1 += rle_modular(arr2, False)
                    rle1 += rle_modular(arr3, False)

                    huff_dict, coded_arr = find_huffman_dict_and_array(rle1)

                    self.out += 'R;'

                    img_bin = string_to_ascii(self.out) + huff_dict + coded_arr

                    self.canvas.destroy()
                    Decompression(self.root, img_bin, self.out, self.filename)

            elif entropy:
                entropy_array = flatten_image(self.image1, not self.vertical)
                entropy_array += flatten_image(self.image2, not self.vertical)
                entropy_array += flatten_image(self.image3, not self.vertical)

                huff_dict, coded_arr = find_huffman_dict_and_array(entropy_array)

                self.out += 'E;'

                img_bin = string_to_ascii(self.out) + huff_dict + coded_arr

                self.canvas.destroy()
                Decompression(self.root, img_bin, self.out, self.filename)


def blockify(image, block_size):
    h, w = image.shape

    h += 0 if h % block_size == 0 else block_size - h % block_size
    w += 0 if w % block_size == 0 else block_size - w % block_size

    h = h // block_size
    w = w // block_size

    out = []

    for i in range(h):
        for j in range(w):
            cur = image[i * block_size:i * block_size + block_size, j * block_size:j * block_size + block_size]

            zigzag_arr = zigzag_optimized(cur, block_size)

            out.append(zigzag_arr)

    return out


def flatten_image(image, horizontal=True):
    h, w = image.shape

    print("FROM RLE END ENTR", image[0, :80:8])

    out = list(np.reshape(image, h * w, order='C' if horizontal else 'F').astype(str))

    return out


def find_huffman_dict_and_array(rle_array):
    freq_dict = get_freq_dict(rle_array)

    codec = HuffmanCodec.from_frequencies(freq_dict)
    huff_dict = HuffmanCodec.get_code_table(codec)

    huff_vals = list(huff_dict.values())
    huff_keys = list(huff_dict.keys())
    dict_vals_binary = parse_touple_values(huff_vals)

    new_dict = {k: v for k, v in zip(huff_keys, dict_vals_binary)}

    huff_code = ''
    for elem in rle_array:
        huff_code += new_dict[elem]  # tuple_to_bin(huff_dict[elem])

    compressed_dict = compress_dict_modular(str(huff_dict))

    return compressed_dict, huff_code


def tuple_to_bin(t):
    bits, val = t

    s = ['0'] * bits
    s = "".join(s)
    val = bin(val)
    val = val.split('b')[1]

    s = s[:-len(val)] + val

    return s


def parse_touple_values(dict_values):
    out = []

    for elem in dict_values:
        bits, val = elem

        s = ['0'] * bits
        s = "".join(s)

        val = bin(val).split('b')[1]

        s = s[:-len(val)] + val

        out.append(s)

    return out
