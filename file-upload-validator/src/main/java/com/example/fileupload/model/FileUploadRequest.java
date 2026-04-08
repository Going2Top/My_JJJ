package com.example.fileupload.model;

import java.io.InputStream;

/**
 * 封装待上传的文件：文件名 + 输入流
 */
public class FileUploadRequest {
    private final String filename;
    private final InputStream inputStream;

    public FileUploadRequest(String filename, InputStream inputStream) {
        this.filename = filename;
        this.inputStream = inputStream;
    }

    public String getFilename() {
        return filename;
    }

    public InputStream getInputStream() {
        return inputStream;
    }
}
