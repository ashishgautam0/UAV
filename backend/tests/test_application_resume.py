"""Exercise the actual application-resume route functions with private storage fixtures."""
import ast
import asyncio
import hashlib
from io import BytesIO
import pathlib
import re
import unittest
import uuid
from fastapi import HTTPException, UploadFile
from fastapi.responses import Response
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

class Bucket:
    def __init__(self):
        self.files = {}
    def upload(self, path, data, options):
        if path in self.files:
            raise RuntimeError("Duplicate capability")
        self.files[path] = data
    def download(self, path):
        return self.files[path]
    def remove(self, paths):
        for path in paths:
            self.files.pop(path, None)

class ResumeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bucket = Bucket()
        class Storage:
            def from_(_, name):
                assert name == "private-fixture"
                return self.bucket
        class Client:
            storage = Storage()
        self.env = dict(re=re, uuid=uuid, hashlib=hashlib, BytesIO=BytesIO,
                        PdfReader=PdfReader, HTTPException=HTTPException,
                        UploadFile=UploadFile, File=lambda _: None, Response=Response,
                        _APPLICATION_LIMIT=3*1024*1024, _PDF_BUCKET="private-fixture",
                        _storage_client=lambda: Client(), _ensure_pdf_bucket=lambda _: None)
        source = pathlib.Path("backend/app/routers/profile.py").read_text()
        wanted = {"_application_path", "save_application_resume",
                  "download_application_resume", "delete_application_resume"}
        nodes = []
        for node in ast.parse(source).body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted:
                node.decorator_list = []
                nodes.append(node)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "<real-routes>", "exec"), self.env)

    def pdf(self):
        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                 NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 20 700 Td (" + b"Python developer with project experience. " * 5 + b") Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
        out = BytesIO()
        writer.write(out)
        return out.getvalue()

    async def test_upload_download_delete_and_reload(self):
        raw = self.pdf()
        saved = await self.env["save_application_resume"](UploadFile(filename="my.pdf", file=BytesIO(raw)))
        self.assertEqual(saved["sha256"], hashlib.sha256(raw).hexdigest())
        response = self.env["download_application_resume"](saved["token"])
        self.assertEqual(response.body, raw)
        self.assertEqual(response.headers["content-disposition"],
                         'attachment; filename="Subidh Khanal Resume.pdf"')
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        self.env["delete_application_resume"](saved["token"])
        with self.assertRaises(HTTPException) as raised:
            self.env["download_application_resume"](saved["token"])
        self.assertEqual(raised.exception.status_code, 404)

    async def test_invalid_replacement_preserves_saved_pdf(self):
        saved = await self.env["save_application_resume"](UploadFile(filename="my.pdf", file=BytesIO(self.pdf())))
        for name, raw in [("bad.pdf", b"not pdf"), ("bad.txt", self.pdf()),
                          ("large.pdf", b"%PDF-" + b"x" * (3*1024*1024))]:
            with self.subTest(name=name):
                with self.assertRaises(HTTPException):
                    await self.env["save_application_resume"](UploadFile(filename=name, file=BytesIO(raw)))
        self.assertTrue(self.env["download_application_resume"](saved["token"]).body)
        self.assertEqual(len(self.bucket.files), 1)

    def test_no_enumeration_or_path_traversal(self):
        for token in ["", "../resume.pdf", "subidh", "a"*31, "A"*32]:
            with self.subTest(token=token):
                with self.assertRaises(HTTPException):
                    self.env["download_application_resume"](token)

    async def test_uploads_have_separate_capabilities(self):
        a = await self.env["save_application_resume"](UploadFile(filename="a.pdf", file=BytesIO(self.pdf())))
        b = await self.env["save_application_resume"](UploadFile(filename="b.pdf", file=BytesIO(self.pdf())))
        self.assertNotEqual(a["token"], b["token"])
        self.env["delete_application_resume"](a["token"])
        self.assertTrue(self.env["download_application_resume"](b["token"]).body)

if __name__ == "__main__":
    unittest.main()
