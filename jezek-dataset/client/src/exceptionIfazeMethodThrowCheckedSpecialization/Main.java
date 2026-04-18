package exceptionIfazeMethodThrowCheckedSpecialization;

import java.io.IOException;

import testing_lib.exceptionIfazeMethodThrowCheckedSpecialization.ExceptionIfazeMethodThrowCheckedSpecialization;

public class Main implements ExceptionIfazeMethodThrowCheckedSpecialization {
	@Override
	public void method1() throws IOException {

	}

	public static void main(String[] args) {
		ExceptionIfazeMethodThrowCheckedSpecialization constr = new ExceptionIfazeMethodThrowCheckedSpecialization() {
			@Override public void method1() {}
		};
		try {
			constr.method1();
		} catch (IOException e) {}
	}

}
