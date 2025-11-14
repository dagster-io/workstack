---
discussion_number: 9542
title: "Intro: What are code smells?"
author: schrockn
created_at: 2024-05-02T13:13:32Z
updated_at: 2024-05-02T13:13:32Z
url: https://github.com/dagster-io/internal/discussions/9542
category: Python Code Smells and Anti-Patterns
---

This is a project to developed a shared sense of taste and standards in our code. To that end I'm going start collecting and writing down best practices. I'll do the first few but I would love to make this a collective effort.
In this case this is a category called code smells. 

Sometimes code smells. Originally joined by Kent Beck it was [defined](https://wiki.c2.com/?CodeSmell) as “a hint that something has gone wrong somewhere in your code”. Here at Dagster Labs we expand that definition to include generalized violations of best practices (hence why the category is “Python Code Smells and Anti-Patterns”)

Code smells are inherently subjective and a matter of taste. By having shared definitions of smells, we develop a collective taste. This means a more coherent, consistent system and––if the code smells are in essence good and accurate––better software.

I'm using github discussions for this content for a few reasons:
* Github discussions tend to have higher quality and more authorative content
* The comment log in particular leads to more thoughtful and structured engagement with the content.
* Comments and discussions about the rules can be as high value as the rules themselves, as they provided invaluable context and supporting evidence. Comments in Notion/gdocs are scattered and liable to be dismissed. Dismissible comments are a blackhole of valuable context. They are designed to destroy information.
* You can directly reference these discussions from PRs and other discussions.