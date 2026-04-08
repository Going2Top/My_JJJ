package com.example.fileupload.validator;

import java.util.HashMap;
import java.util.Map;

/**
 * 校验器工厂：根据文件扩展名返回对应的校验器
 */
public class FileValidatorFactory {

    private final Map<String, FileValidator> validators = new HashMap<>();

    public FileValidatorFactory() {
        register(new TxtFileValidator());
        register(new ZipFileValidator());
        register(new PropertiesFileValidator());
        register(new SqlFileValidator());
        register(new YamlFileValidator());
    }

    private void register(FileValidator validator) {
        validators.put(validator.getSupportedExtension().toLowerCase(), validator);
    }

    /**
     * 根据文件名获取对应校验器，不支持的类型返回 null
     */
    public FileValidator getValidator(String filename) {
        String ext = extractExtension(filename);
        return validators.get(ext);
    }

    public boolean isSupported(String filename) {
        return validators.containsKey(extractExtension(filename));
    }

    private String extractExtension(String filename) {
        if (filename == null || !filename.contains(".")) {
            return "";
        }
        return filename.substring(filename.lastIndexOf('.') + 1).toLowerCase();
    }
}
