package com.example.crossserver.workerbatch;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import org.springframework.stereotype.Service;

@Service
public class ReverseTextService {

    public void reverseText(Path inputPath, Path outputPath) throws IOException {
        String content = Files.readString(inputPath, StandardCharsets.UTF_8);
        Path parent = outputPath.getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
        Files.writeString(outputPath, new StringBuilder(content).reverse().toString(), StandardCharsets.UTF_8);
    }
}
