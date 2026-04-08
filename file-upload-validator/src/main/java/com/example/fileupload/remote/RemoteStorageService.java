package com.example.fileupload.remote;

import java.io.InputStream;

/**
 * 远端存储服务接口
 */
public interface RemoteStorageService {

    /**
     * 将文件流存储到远端
     *
     * @param filename    目标文件名
     * @param inputStream 文件输入流（调用方保证流未消费）
     * @return 远端存储路径
     */
    String store(String filename, InputStream inputStream);
}
