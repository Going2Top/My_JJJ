package com.example.fileupload.remote;

import java.io.IOException;
import java.io.InputStream;
import java.util.concurrent.ConcurrentHashMap;
import java.util.Map;

/**
 * 模拟远端存储：将文件内容保存到内存 Map，记录字节数
 * 实际场景替换为 S3 / OSS / SFTP 等实现即可
 */
public class MockRemoteStorageService implements RemoteStorageService {

    private static final String REMOTE_BASE_PATH = "remote://mock-bucket/uploads/";

    // 存储已上传文件的元信息：filename -> 字节数
    private final Map<String, Long> uploadedFiles = new ConcurrentHashMap<>();

    @Override
    public String store(String filename, InputStream inputStream) {
        try {
            long byteCount = 0;
            byte[] buffer = new byte[4096];
            int read;
            while ((read = inputStream.read(buffer)) != -1) {
                byteCount += read;
            }
            String remotePath = REMOTE_BASE_PATH + filename;
            uploadedFiles.put(filename, byteCount);
            System.out.printf("[MockStorage] 已上传: %s -> %s (%d bytes)%n",
                    filename, remotePath, byteCount);
            return remotePath;
        } catch (IOException e) {
            throw new RuntimeException("模拟远端存储失败: " + e.getMessage(), e);
        }
    }

    /** 用于测试断言：查询某文件是否已上传 */
    public boolean isUploaded(String filename) {
        return uploadedFiles.containsKey(filename);
    }

    /** 用于测试断言：查询已上传文件的字节数 */
    public long getUploadedSize(String filename) {
        return uploadedFiles.getOrDefault(filename, -1L);
    }

    /** 清空上传记录（测试用） */
    public void clear() {
        uploadedFiles.clear();
    }
}
