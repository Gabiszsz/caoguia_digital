package com.ifgoiano.urt.projetocaoguia.projetocaoguiabackend.postagemInstagram.controller;

import com.ifgoiano.urt.projetocaoguia.projetocaoguiabackend.postagemInstagram.model.PostagemInstagram;
import com.ifgoiano.urt.projetocaoguia.projetocaoguiabackend.postagemInstagram.repository.InstagramRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/instagram")
@RequiredArgsConstructor
@Tag(name = "Instagram", description = "Endpoints para sincronização e gerenciamento de postagens do Instagram")
public class InstagramController {

    private final InstagramRepository repository;

    @PostMapping("/sincronizar")
    @Operation(summary = "Recebe e salva postagens do Instagram via script Python")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<PostagemInstagram> sincronizar(@RequestBody PostagemInstagram postagem) {
        PostagemInstagram novaPostagem = repository.save(postagem);
        return ResponseEntity.ok(novaPostagem);
    }
}