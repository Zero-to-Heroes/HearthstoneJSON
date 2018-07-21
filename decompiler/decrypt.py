#!/usr/bin/env python

import binascii
import sys
import blowfish
import pefile

# Standard PE header (consists of the PE signature and COFF header)
PE_VALID_SIGN = b"PE\0\0"
PE_SIGN_LENGTH = len(PE_VALID_SIGN)  # PE Signature is encoded within 4 bytes

# Decryption data
KEY_LEN = 0x38
KEY_PADDING = KEY_LEN + 0x5  # Offset from end of the file


def get_pe_offset(buf):
	"""
	Returns the byte position within buf where the PE header can be found.
	"""

	# DOS Header
	_DOS_PE_OFFSET = 0x3C  # Field containing the PE header offset
	_DOS_PTR_LENGTH = 0x4  # The offset is encoded within 4 bytes (little-endian)

	pe_offset_bytes = buf[_DOS_PE_OFFSET: (_DOS_PE_OFFSET + _DOS_PTR_LENGTH)]
	return int.from_bytes(pe_offset_bytes, 'little')


def get_pe_signature(buf):
	"""
	Returns a slice of the provided buffer representing the PE header signature.
	"""

	pe_offset = get_pe_offset(buf)
	return buf[pe_offset: (pe_offset + PE_SIGN_LENGTH)]


def valid_pe_signature(buf):
	"""
	Overwrites the PE header signature of the provided buffer.
	A new buffer is returned because buffer (bytes) objects are immutable.
	"""

	pe_offset = get_pe_offset(buf)
	return buf[:pe_offset] + PE_VALID_SIGN + buf[(pe_offset + PE_SIGN_LENGTH):]


def get_decryption_key(buf):
	"""
	Returns the embedded encryption key from the provided library.
	"""

	key_offset = len(buf) - KEY_PADDING
	return key_offset, buf[key_offset: (key_offset + KEY_LEN)]


def get_encrypted_parts(buf):
	"""
	Returns slices of encrypted parts of the buffer.
	"""

	encrypted_slices = []
	# Write a valid signature so the pefile module can parse the buffer
	# correctly.
	buf = valid_pe_signature(buf)
	pe = pefile.PE(data=buf, fast_load=True)

	header_size = pe.OPTIONAL_HEADER.SizeOfHeaders
	print("Header size: 0x{:02X}".format(header_size))

	for section in pe.sections:
		str_section_name = section.Name.decode('ascii')
		# Section names are ALWAYS 8 bytes long, unless the contain a reference
		# indicated with a backslash.
		if section.Name == b".text\x00\x00\x00":
			offset = section.PointerToRawData
			length = section.SizeOfRawData
			print("Section {!s}: Targetted for decryption".format(str_section_name))
			print("--- Offset: {}, Length: {}".format(offset, length))
			encrypted_slices.append((offset, buf[offset: (offset + length)]))
		else:
			print("Section {!s}: skipped".format(str_section_name))

	return encrypted_slices


def decrypt(input_filepath, output_filepath):
	"""
	Attempts to decrypt the input_file library.
	The input file is supposed to be a DLL, containing encrypted sections.
	This method will extract the decryption key and decrypt the library and write
	an equivalent unencrypted library at the output_file location.
	"""

	with open(input_filepath, "rb") as f:
		buf = f.read()

	# A valid PE signature means the input file is not encrypted!
	pe_sign = get_pe_signature(buf)
	if pe_sign == PE_VALID_SIGN:
		print("File is not encrypted")
		write_decrypted_output(buf, output_filepath)
		return False

	print("Decrypting {!r}".format(input_filepath))
	key_offset, key = get_decryption_key(buf)
	print("Key: {!r}".format(binascii.hexlify(key)))

	# Some parts of the file are NOT encrypted!
	encrypted_parts = get_encrypted_parts(buf)

	for enc_offset, enc_data in encrypted_parts:
		cipher = blowfish.Cipher(key)
		# decrypt_ecb returns an iterator of byte data.
		decrypted = b"".join(cipher.decrypt_ecb(enc_data))
		# Merge with buf
		buf = buf[:enc_offset] + decrypted + buf[(enc_offset + len(decrypted)):]

	# At this point buf contains the properly decrypted library.
	write_decrypted_output(buf, output_filepath)

	return True


def write_decrypted_output(buf, output_filepath):
	"""
	Writes the decrypted library contents to the output file.
	"""

	# Make sure the PE signature is valid.
	buf = valid_pe_signature(buf)
	with open(output_filepath, "wb") as f:
		f.write(buf)

	print("Written to {!r}".format(output_filepath))


def main():
	decrypt(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
	main()
