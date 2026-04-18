package exceptionClazzMethodThrowCheckedSpecialization;

import java.io.IOException;

import testing_lib.exceptionClazzMethodThrowCheckedSpecialization.ExceptionClazzMethodThrowCheckedSpecialization;

public class Main extends ExceptionClazzMethodThrowCheckedSpecialization {
	@Override
	public void method1() throws IOException {

	}

	public static void main(String[] args) {
		ExceptionClazzMethodThrowCheckedSpecialization constr = new ExceptionClazzMethodThrowCheckedSpecialization();
		try {
			constr.method1();
		} catch (IOException e) {}
	}
}
