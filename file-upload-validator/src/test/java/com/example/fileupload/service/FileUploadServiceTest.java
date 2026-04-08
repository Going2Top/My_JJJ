package com.example.fileupload.service;

import com.example.fileupload.model.BatchUploadResult;
import com.example.fileupload.model.FileUploadRequest;
import com.example.fileupload.model.FileUploadResult;
import com.example.fileupload.remote.MockRemoteStorageService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("FileUploadService 集成测试")
class FileUploadServiceTest {

    private MockRemoteStorageService mockStorage;
    private FileUploadService service;

    @BeforeEach
    void setUp() {
        mockStorage = new MockRemoteStorageService();
        service = new FileUploadService(mockStorage);
    }

    // ==================== 单文件上传 ====================

    @Test
    @DisplayName("上传合法 TXT -> 成功且远端已存储")
    void uploadValidTxt() {
        byte[] content = "Hello, 世界！".getBytes(StandardCharsets.UTF_8);
        FileUploadResult result = service.upload(new FileUploadRequest("test.txt",
                new ByteArrayInputStream(content)));

        assertThat(result.isSuccess()).isTrue();
        assertThat(mockStorage.isUploaded("test.txt")).isTrue();
        assertThat(mockStorage.getUploadedSize("test.txt")).isEqualTo(content.length);
    }

    @Test
    @DisplayName("上传合法 ZIP -> 成功")
    void uploadValidZip() throws IOException {
        byte[] zipBytes = buildZip("readme.txt", "Hello");
        FileUploadResult result = service.upload(new FileUploadRequest("archive.zip",
                new ByteArrayInputStream(zipBytes)));

        assertThat(result.isSuccess()).isTrue();
        assertThat(mockStorage.isUploaded("archive.zip")).isTrue();
    }

    @Test
    @DisplayName("上传合法 Properties -> 成功")
    void uploadValidProperties() {
        byte[] content = "app.name=demo\napp.version=1.0".getBytes(StandardCharsets.UTF_8);
        FileUploadResult result = service.upload(new FileUploadRequest("app.properties",
                new ByteArrayInputStream(content)));

        assertThat(result.isSuccess()).isTrue();
    }

    @Test
    @DisplayName("上传合法 SQL -> 成功")
    void uploadValidSql() {
        byte[] content = "SELECT * FROM users;\nINSERT INTO logs VALUES (1);".getBytes(StandardCharsets.UTF_8);
        FileUploadResult result = service.upload(new FileUploadRequest("init.sql",
                new ByteArrayInputStream(content)));

        assertThat(result.isSuccess()).isTrue();
    }

    @Test
    @DisplayName("上传合法 YAML -> 成功")
    void uploadValidYaml() {
        byte[] content = "server:\n  port: 8080\nname: demo".getBytes(StandardCharsets.UTF_8);
        FileUploadResult result = service.upload(new FileUploadRequest("config.yaml",
                new ByteArrayInputStream(content)));

        assertThat(result.isSuccess()).isTrue();
    }

    // ==================== 校验失败场景 ====================

    @Test
    @DisplayName("TXT 文件内容为二进制 -> 校验失败，不上传远端")
    void uploadInvalidTxt() {
        byte[] content = {(byte) 0xFF, (byte) 0xFE, (byte) 0x80, (byte) 0x81};
        FileUploadResult result = service.upload(new FileUploadRequest("bad.txt",
                new ByteArrayInputStream(content)));

        assertThat(result.isSuccess()).isFalse();
        assertThat(mockStorage.isUploaded("bad.txt")).isFalse();
    }

    @Test
    @DisplayName("ZIP 文件魔数错误 -> 校验失败")
    void uploadInvalidZip() {
        byte[] content = "Not a zip".getBytes();
        FileUploadResult result = service.upload(new FileUploadRequest("fake.zip",
                new ByteArrayInputStream(content)));

        assertThat(result.isSuccess()).isFalse();
        assertThat(result.getMessage()).contains("失败");
    }

    @Test
    @DisplayName("不支持的文件类型（.exe）-> 失败")
    void uploadUnsupportedType() {
        byte[] content = "some binary".getBytes();
        FileUploadResult result = service.upload(new FileUploadRequest("virus.exe",
                new ByteArrayInputStream(content)));

        assertThat(result.isSuccess()).isFalse();
        assertThat(result.getMessage()).contains("不支持的文件类型");
    }

    // ==================== 流只读一次的核心验证 ====================

    @Test
    @DisplayName("流只能读一次 - 验证 byte[] 缓冲方案正确工作（校验+上传都使用同一份内容）")
    void streamCanOnlyBeReadOnce_bufferSolvesIt() throws IOException {
        // 构建一个真实内容用于断言大小
        byte[] originalContent = "key=value\nfoo=bar".getBytes(StandardCharsets.UTF_8);

        // 使用普通 ByteArrayInputStream（可重读，但模拟真实场景：只当作一次性流）
        ByteArrayInputStream stream = new ByteArrayInputStream(originalContent);

        FileUploadResult result = service.upload(new FileUploadRequest("config.properties", stream));

        // 校验通过 + 上传成功
        assertThat(result.isSuccess()).isTrue();
        // 远端收到的字节数与原始内容一致，说明上传阶段流没有被截断
        assertThat(mockStorage.getUploadedSize("config.properties")).isEqualTo(originalContent.length);
    }

    // ==================== 批量上传 ====================

    @Test
    @DisplayName("批量上传：3 合法 + 1 非法 -> 汇总结果正确")
    void batchUploadMixed() throws IOException {
        List<FileUploadRequest> requests = Arrays.asList(
            new FileUploadRequest("a.txt",
                new ByteArrayInputStream("valid text".getBytes(StandardCharsets.UTF_8))),
            new FileUploadRequest("b.properties",
                new ByteArrayInputStream("k=v".getBytes(StandardCharsets.UTF_8))),
            new FileUploadRequest("c.yaml",
                new ByteArrayInputStream("name: test".getBytes(StandardCharsets.UTF_8))),
            new FileUploadRequest("d.zip",
                // 故意传入非法 zip
                new ByteArrayInputStream("not a zip content".getBytes()))
        );

        BatchUploadResult batchResult = service.uploadBatch(requests);

        System.out.println(batchResult);

        assertThat(batchResult.getTotal()).isEqualTo(4);
        assertThat(batchResult.getSuccessCount()).isEqualTo(3);
        assertThat(batchResult.getFailCount()).isEqualTo(1);
        // 合法文件确认上传到远端
        assertThat(mockStorage.isUploaded("a.txt")).isTrue();
        assertThat(mockStorage.isUploaded("b.properties")).isTrue();
        assertThat(mockStorage.isUploaded("c.yaml")).isTrue();
        // 非法文件不应上传
        assertThat(mockStorage.isUploaded("d.zip")).isFalse();
    }

    @Test
    @DisplayName("批量上传全部合法文件 -> 全部成功")
    void batchUploadAllValid() throws IOException {
        List<FileUploadRequest> requests = Arrays.asList(
            new FileUploadRequest("readme.txt",
                new ByteArrayInputStream("Hello World".getBytes(StandardCharsets.UTF_8))),
            new FileUploadRequest("schema.sql",
                new ByteArrayInputStream("CREATE TABLE t (id INT);".getBytes(StandardCharsets.UTF_8))),
            new FileUploadRequest("app.yaml",
                new ByteArrayInputStream("debug: true".getBytes(StandardCharsets.UTF_8))),
            new FileUploadRequest("archive.zip",
                new ByteArrayInputStream(buildZip("f.txt", "content")))
        );

        BatchUploadResult batchResult = service.uploadBatch(requests);

        assertThat(batchResult.getSuccessCount()).isEqualTo(4);
        assertThat(batchResult.getFailCount()).isEqualTo(0);
    }

    // ==================== 工具方法 ====================

    private byte[] buildZip(String entryName, String entryContent) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(baos)) {
            zos.putNextEntry(new ZipEntry(entryName));
            zos.write(entryContent.getBytes());
            zos.closeEntry();
        }
        return baos.toByteArray();
    }
}
